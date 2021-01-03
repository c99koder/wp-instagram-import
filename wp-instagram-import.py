#!/usr/bin/python3

#  Copyright (C) 2021 Sam Steele
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import requests, sys, os, re
from datetime import datetime, date, timedelta
from instaloader import instaloader, Profile
from wordpress import API
from slugify import slugify

INSTAGRAM_PROFILE = ''
WORDPRESS_URL = 'https://'
WORDPRESS_USER = ''
WORDPRESS_PASS = ''
WORDPRESS_CATEGORY = 'Photos'
DOWNLOAD_PATH = '/tmp'

L = instaloader.Instaloader()
wpapi = API(
    url=WORDPRESS_URL,
    api="wp-json",
    version='wp/v2',
    wp_user=WORDPRESS_USER,
    wp_pass=WORDPRESS_PASS,
    basic_auth = True,
    user_auth = True,
    consumer_key = "",
    consumer_secret = ""
)
category_id = -1
tags = {}

def create_tag(name):
	p = wpapi.post("tags", 
		{
			'name': name
		})
	assert p.status_code == 201, "Unable to create WordPress tag"
	print("Created tag ID %i" % (p.json()['id']))
	return p.json()['id']

def create_media(filename, content_type, post_id, date_utc):
	assert os.path.exists(filename), "media file not found"
	data = open(filename, 'rb').read()
	p = wpapi.post("media", data, headers={
	    'cache-control': 'no-cache',
	    'content-disposition': 'attachment; filename=%s' % (os.path.basename(filename)),
	    'content-type': '%s' % (content_type)
	})
	assert p.status_code == 201, "Unable to upload WordPress media"
	p = wpapi.post("media/" + str(p.json()['id']), 
		{
			'status': 'publish',
			'date_gmt': date_utc.isoformat(),
			'post': str(post_id)
		})
	assert p.status_code == 200, "Unable to update WordPress media"
	print("Created media ID %i" % (p.json()['id']))
	return p.json()['id']

def create_post(post):
	title = post.caption
	content = '[gallery link="file" size="large" columns="1"][playlist type=video]'
#	split = post.caption.partition('\n')
#	title = split[0]
#	content = split[2] + split[1] + content

	while re.search('\s#\w+$', title) != None:
		title = re.sub('\s#\w+$', '', title)
		pass

	title = re.sub('\n$', '', title)
	print("Title: " + title)
	print("Content: " + content)

	post_tags = []
	for hashtag in post.caption_hashtags:
		slug = slugify(hashtag.lower())
		if slug in tags.keys():
			post_tags.append(tags[slug])
		else:
			tag_id = create_tag(hashtag)
			tags[slug] = tag_id
			post_tags.append(tag_id)

	p = wpapi.post("posts", 
		{
			'status': 'publish',
			'date_gmt': post.date_utc.isoformat(),
			'format': 'gallery',
			'categories': [str(category_id)],
			'content': content,
			'title': title,
			'tags': post_tags
		})
	assert p.status_code == 201, "Unable to create WordPress post"
	print("Created post ID %i" % (p.json()['id']))
	return p.json()['id']

def upload(post_id, url, extension, mime_type, date_utc):
	print("Downloading %s to %s/%i%s" % (url, DOWNLOAD_PATH, post_id, extension))
	result = L.download_pic(filename=DOWNLOAD_PATH + "/" + str(post_id), url=url, mtime=date_utc)
	assert result == True, "Download failed"
	create_media(DOWNLOAD_PATH + "/" + str(post_id) + extension, mime_type, post_id, date_utc)
	os.remove(DOWNLOAD_PATH + "/" + str(post_id) + extension)

def upload_image(post):
	post_id = create_post(post)
	upload(post_id, post.url, ".jpg", "image/jpeg", post.date_utc)


def upload_video(post):
	post_id = create_post(post)
	upload(post_id, post.video_url, ".mp4", "video/mp4", post.date_utc)

def upload_sidecar(post):
	post_id = create_post(post)
	for node in post.get_sidecar_nodes():
		if node.is_video:
			upload(post_id, node.video_url, ".mp4", "video/mp4", post.date_utc)
		else:
			upload(post_id, node.display_url, ".jpg", "image/jpeg", post.date_utc)


categories = wpapi.get("categories")
assert categories.status_code == 200, "Unable to fetch categories from WordPress"
for c in categories.json():
	if c['name'] == WORDPRESS_CATEGORY:
		category_id = c['id']
		print("Found %s category ID: %i" % (WORDPRESS_CATEGORY, category_id))
		break

assert category_id != -1, "Unable to find requested WordPress category"

posts = wpapi.get("posts?per_page=1&categories=" + str(category_id))
assert posts.status_code == 200, "Unable to fetch posts from WordPress"

latest_post_date = datetime.fromisoformat(posts.json()[0]['date_gmt'] + "+00:00")
print("Most recent post in category: %s" % (latest_post_date))

page = 0
while True:
	page = page + 1
	t = wpapi.get("tags?per_page=100&page=" + str(page))
	assert t.status_code == 200, "Unable to load tags from WordPress"
	for tag in t.json():
		if tag['taxonomy'] == 'post_tag':
			tags[tag['slug']] = tag['id']
	if len(t.json()) == 100:
		pass
	else:
		break

print("Fetched %i tags from WordPress" % len(tags))

print("Fetching Instagram profile for %s" % (INSTAGRAM_PROFILE))
profile = Profile.from_username(L.context, INSTAGRAM_PROFILE)
posts = profile.get_posts()

for post in posts:
	if datetime.fromisoformat(post.date_utc.isoformat() + "+00:00") > latest_post_date:
		if post.typename == "GraphImage":
			upload_image(post)
		elif post.typename == "GraphVideo":
			upload_video(post)
		elif post.typename == "GraphSidecar":
			upload_sidecar(post)
		else:
			print("Unsupported post type: %s" % (post.typename))
	else:
		break
