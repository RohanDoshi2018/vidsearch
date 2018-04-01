# VidSearch - Search for objects and speech within your videos!

The world produces more and more video each day. In fact, 300 hours of YouTube is uploaded every minute. But, labeling each frame (e.g. key objects and words) and indexing it manually is impossible, making it difficult to find what you really want in your sea of videos.

Examples of The Problem:
1. Film producers lose hundreds of hours watching footage to find the right clip.
2. Families lose valuable time going through all their old footage to find the right content.
3. Guards are unable to watch hundreds of days of security footage to find hints of criminal activity.

What if we could automate the labeling and indexing of video footage - both the audio and visual elements - for later search and retrieval? This hack has taken on that ambitious technical challenge. Thanks to the recent development of deep learning APIs in the computer vision and natural language processing domain, this is now possible.

Users upload videos. Our system goes frame by frame, breaking the video into coherent shots (~5 seconds), and extract visual labels via object recognition and audio transcripts via speech recognition. All of these "tags" are stored along with time stamps in a NoSQL server. Lastly, we created a custom search algorithm to filter through these tags and find the specific video scene among all your videos with the information you are looking for.

Technologies:

NoSQL: Google Cloud Datastore

Audio/Video Media Storage: Google Cloud Storage

Video Object Recognition: Google Cloud Video Intelligence

Video To Audio: ffmpeg, sox

Audio To Text: Google Speech API

Web Framework: Flask

Frontend: jQuery