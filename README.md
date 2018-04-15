# VidSearch - Search for objects and speech in your videos

## Installation

install conda 3.6.3 for OSX

make sure you have vidsearch_service_account.json in the main vidsearch folder you cloned from GitHub

conda create --name vidsearch --file requirements.txt

source activate vidsearch

Install the Google Cloud SDK (install folder locally): https://cloud.google.com/sdk/docs/quickstart-macos

source ~/.bashrc

pip install --upgrade google-cloud-videointelligence

pip install --upgrade google-cloud-datastore

pip install --upgrade google-cloud-storage

pip install --upgrade google-cloud-speech

pip install moviepy

bash run.sh


## Inspiration
Imagine you are a parent digging through countless family recordings for a memory. Or, a video producer painstakingly scrubbing through hundreds of hours of content for a scene. Or,  a guard looking through a barrage of security footage for criminal activity.

The world produces an enormous and growing amount of video. Each minute, 300 hours of YouTube is uploaded. But, it is difficult, time-consuming, and expensive to label each frame for search and retrieval later.

There is so much video to search through, but not enough time. What if we gave you a system that automated the  indexing and labeling of visual objects and spoken speech in your videos so you can search through it later? Introducing: VidSearch.

## What it does

Users upload videos. Our system goes frame by frame, breaking the video into coherent shots (~5 seconds), and extracts visual labels via an object recognition API and audio transcripts via a speech recognition API. All of these "search tags" are stored along with time stamps in a NoSQL server. Lastly, we created a custom search algorithm to filter through these tags and find the specific video scene among all your videos with the information you are looking for.

## How I built it

This was an ambitious technical challenge. We uploaded the audio and video media to the cloud using Google Cloud Storage. For object detection, we used Google Cloud Video Intelligence. For speech recognition, we used the Google Speech API. On the server, we leveraged jjmpeg and sox to standardize the encodings and the audio/video file formats for compatibility with the various APIS. After processing the media, we stored the search tags in a NoSQL server hosted on Google Cloud Datastore; we apply filtering to this server and then our custom search algorithm to score the relevance of each video scene in relation to a search query.

Our webapp was built on the Python Flask framework, and our frontend relied on jQuery and HTML5.

## Challenges I ran into / Accomplishments that I'm proud of

1. Developing a custom search algorithm. For each video clip, we have extracted textual labels (from the object detection and audio transcript). We summate the similarity scores between each synset of the words in the search query and the labels from the video. Then, this score is weighed by the confidence score of the labels.We output a final score for the video clip, which is then ranked from highest to lowest.

2. Architecting the Storage, View, Controller, and API components to minimize the number of network calls to reduce latency.

3. Standardizing file encodings and file types in preprocessing to make the object detection and audio recognition APIs work.

## What I learned

How to build a complex web-app from end-to-end while integrating deep learning APIs