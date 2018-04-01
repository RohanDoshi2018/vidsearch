import os
import io
import sys
import time
import json
import subprocess
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from google.cloud import storage, datastore, videointelligence, speech 
from google.cloud.speech import enums, types
import moviepy.editor as mp
# import gensim
from nltk.corpus import wordnet

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['mov', 'mpeg4', 'mp4', 'avi'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Serve the homepage, a static file
@app.route("/")
def index():
  return render_template('index.html')

# Serve static files
@app.route('/<path:path>')
def static_proxy(path):
  # send_static_file will guess the correct MIME type
  return app.send_static_file(path)

@app.route("/upload_video", methods=['POST'])
def upload_video():

  file = request.files['file']
  filetype = file.filename.rsplit('.', 1)[1].lower() 
  upload_time = time.time()

  if file and allowed_file(file.filename, filetype):
    video_id = request.form['video_id'] + '.' + filetype
    orig_filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_id))

    vid_metadata = {
      'video_id': video_id,  
      'orig_filename': orig_filename,
      'upload_time': upload_time,
      'status': 'Processing',
    }

    # add vid_entity entity to NoSQL database
    client = datastore.Client() # instantiates a client

    kind = 'media' # the kind for the new entity
    name = video_id # the name/ID for the new entity
    key = client.key(kind, name) # create key for the new entity

    vid_entity = datastore.Entity(key=key) # initialize entity
    vid_entity.update(vid_metadata) # fill in the entity
    client.put(vid_entity) # client uploads the entity

    return json.dumps(vid_metadata), 200, {'ContentType':'application/json'} 

  return json.dumps({'error': 'invalid file'}), 404, {'ContentType':'application/json'} 


@app.route("/get_uploads")
def get_uploads():
  # return all uploads (list of json objects)
  client = datastore.Client() # instantiates a client
  query = client.query(kind='media')
  query.order = ['upload_time']
  uploads = list(query.fetch())
  return  json.dumps({'uploads':uploads}), 200, {'ContentType':'application/json'}

@app.route("/process_video")
def process_video():
    video_id = request.args.get('video_id') # TODO: is this correct

    print("Getting Tags", file=sys.stderr)

    # extract visual labels and store as search tags
    label_tags = extract_labels(video_id)

    # extract speech transcripts and store as search tags
    speech_tags = extract_speech(video_id)

    all_tags = label_tags + speech_tags

    print("Storing Tags", file=sys.stderr)
    store_search_tags(video_id, all_tags)

    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

def extract_labels(video_id):
    video_prefix = video_id.split('.')[0]
    video_id_path = os.path.join(app.config['UPLOAD_FOLDER'], video_id)

    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.enums.Feature.LABEL_DETECTION]
    video_id_path = os.path.join(app.config['UPLOAD_FOLDER'], video_id)
    with io.open(video_id_path, 'rb') as movie:
        input_content = movie.read()
    operation = video_client.annotate_video(features=features, input_content=input_content)
    result = operation.result(timeout=90)

    shot_labels = result.annotation_results[0].shot_label_annotations
    tags = []

    for i, shot_label in enumerate(shot_labels):

        tag_text = []
        tag_text.append(shot_label.entity.description)
        tag_text.append(';')

        for category_entity in shot_label.category_entities:
            tag_text.append(category_entity.description)
            tag_text.append(';')

        tag_text = (' ').join(tag_text)

        max_confidence, max_start_time, max_end_time = 0, 0, 0
        for i, shot in enumerate(shot_label.segments):
            start_time = (shot.segment.start_time_offset.seconds +
                          shot.segment.start_time_offset.nanos / 1e9)
            end_time = (shot.segment.end_time_offset.seconds +
                        shot.segment.end_time_offset.nanos / 1e9)
            confidence = shot.confidence

            if confidence > max_confidence:
                max_confidence = confidence
                max_start_time = start_time
                max_end_time = end_time

        tags.append({
          'video_id': video_id,  
          'tag_type': 'label',
          'confidence': max_confidence,
          'content': tag_text,
          'start_time': max_start_time,
          'end_time': max_end_time,
        })

    return tags 

def extract_speech(video_id):
    video_prefix = video_id.split('.')[0]
    video_id_path = os.path.join(app.config['UPLOAD_FOLDER'], video_id)

    # turn video file into mp3
    vid = mp.VideoFileClip(video_id_path)
    mp3_filename =  video_prefix + '.mp3'
    mp3_path = os.path.join(app.config['UPLOAD_FOLDER'], mp3_filename)
    vid.audio.write_audiofile(mp3_path)

    wav_path = video_prefix + '.wav'
    wav_mono_path = video_prefix + '_mono.wav'

    wav_path = os.path.join(app.config['UPLOAD_FOLDER'], wav_path)
    wav_mono_path = os.path.join(app.config['UPLOAD_FOLDER'], wav_mono_path)

    # mp3 -> wav (1 channel)
    # ffmpeg -i uploads/jane_test.mp3 -ar 48000 uploads/jane_test.wav 
    # sox uploads/jane_test.wav -c 1 uploads/jane_test_1.wav
    mp3_command = ['ffmpeg', '-i', mp3_path, '-ar', '48000', wav_path]
    one_channel_command = ['sox', wav_path, '-c', '1', wav_mono_path] 

    subprocess.call(mp3_command)
    subprocess.call(one_channel_command)

    # upload wav to Google Cloud Storage to get GCS URI
    bucket_name = "vidsearch"
    source_file_name = wav_mono_path
    destination_blob_name = video_prefix + '.wav'
    upload_blob(bucket_name, source_file_name, destination_blob_name)

    gcs_uri = 'gs://vidsearch/' + destination_blob_name

    # Asynchronously transcribes the audio file specified by the gcs_uri
    client = speech.SpeechClient()

    audio = types.RecognitionAudio(uri=gcs_uri)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        language_code='en-US',
        enable_word_time_offsets=True)

    operation = client.long_running_recognize(config, audio)

    response = operation.result(timeout=90)
    tags = []
    for result in response.results:

        # the first alternative is the most likely one for this portion.
        transcript = result.alternatives[0].transcript
        confidence = result.alternatives[0].confidence
        word_metadata = result.alternatives[0].words
        start_time = word_metadata[0].start_time.seconds
        end_time = word_metadata[-1].end_time.seconds

        tags.append({
          'video_id': video_id,  
          'tag_type': 'speech',
          'confidence': confidence,
          'content': transcript,
          'start_time': start_time,
          'end_time': end_time,
        })

    return tags

# store search tags from label/speech extraction in Google Cloud Datastore
def store_search_tags(video_id, tags):
  # add vid_entity entity to NoSQL database
  client = datastore.Client() # instantiates a client

  for tag in tags:

    # upload search tag
    key = client.key('search_tags') # create key for the new entity
    vid_entity = datastore.Entity(key=key) # initialize entity
    vid_entity.update(tag) # fill in the entity
    client.put(vid_entity) # client uploads the entity

    # update processing status
    key = client.key('media', video_id)
    vid_entity = client.get(key)
    vid_entity['status'] = 'Processed'
    client.put(vid_entity)

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to a Google Cloud Storage bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

@app.route("/search")
def search_video():
  
  print("Searching Tags", file=sys.stderr)
  
  q = request.args.get('q')
  q_arr = q.strip().split(' ')

  # fetch all tags
  client = datastore.Client() # instantiates a client
  query = client.query(kind='search_tags')
  query.add_filter('confidence', '>=', .5)
  search_tags = list(query.fetch())

  tag_scores = []

  for tag in search_tags:
      score = get_tag_score(q, tag['content'], tag['confidence'])

      print("score", file=sys.stderr)
      print(score, file=sys.stderr)

      # extract info from tags
      tag_dict = {
        'video_id': tag['video_id'],
        'content': tag['content'],
        'start_time': tag['start_time'],
        'end_time': tag['end_time'],
        'score': score,
      }

      tag_scores.append(tag_dict)

  # sort tags by score; take top 20
  num_elem = min(20, len(tag_scores)-1)
  ans = sorted(tag_scores, key=lambda k: k['score'], reverse=True)[:num_elem]

  return json.dumps(ans), 200, {'ContentType':'application/json'}

def get_tag_score(query, text, confidence):
    """ calculate the tag score based on the query as well as the the tag's text and confidence """

    # tokenize the query and text
    query = query.strip().split(' ')
    text = text.strip().split(' ')
    text = [x for x in text if x != ';']

    return confidence * sent_similarity(query, text)

def sent_similarity(a,b):
    """ calculate the average cosine similarity for list of words a and b """
    score_list = []

    for w1 in a:
        for w2 in b:
            sim = word_similarity(w1, w2)
            score_list.append(sim)
    if sum(score_list) == 0 or len(score_list) == 0:
      return 0
    else:
      return sum(score_list) / len(score_list)

def word_similarity(wordOne, wordTwo):
  synOne = wordnet.synsets(wordOne)
  synTwo = wordnet.synsets(wordTwo)
  score = 0
  scoreList = []
  for indexOne in range (0, len(synOne)):
    for indexTwo in range (0, len(synTwo)):
      score = synOne[indexOne].wup_similarity(synTwo[indexTwo])
      if score is not None:
        scoreList.append(score)
  sum = 0
  for num in scoreList:
    sum = sum + num

  if len(scoreList) == 0:
    return 0
  else: 
    return sum / (len(scoreList))

def allowed_file(filename, filetype):
    return '.' in filename and filetype in ALLOWED_EXTENSIONS

def upload_blob(bucket_name, source_file_name, destination_blob_name):
  """Uploads a file to the bucket."""
  storage_client = storage.Client()
  bucket = storage_client.get_bucket(bucket_name)
  blob = bucket.blob(destination_blob_name)
  blob.upload_from_filename(source_file_name)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Run the server app
if __name__ == "__main__":
  app.run(debug = True)