#!/usr/bin/env python3

#  Copyright (C) 2022 Sam Steele
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

import requests, sys, os, re, subprocess, json
from datetime import datetime, date, timedelta
from instaloader import instaloader, Profile
from slugify import slugify

INSTAGRAM_PROFILE = ''
WP_CLI = '/usr/bin/wp'
WORDPRESS_PATH = '/var/www/html'
WORDPRESS_CATEGORY = 'Photos'
WORDPRESS_USER = 'admin'
DOWNLOAD_PATH = '/tmp'

L = instaloader.Instaloader()
L = instaloader.Instaloader()
try:
    L.load_session_from_file(INSTAGRAM_PROFILE)
except FileNotFoundError:
    print("Logging into Instagram can make this script more reliable. Try: instaloader -l {INSTAGRAM_PROFILE}")
category_id = -1
user_id = -1
tags = {}

def create_tag(name):
	t = subprocess.run([WP_CLI, 'term', 'create', 'post_tag', name, '--porcelain', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
	assert t.returncode == 0, "Unable to create WordPress tag"
	print("Created tag ID %i" % (int(t.stdout)))
	return int(t.stdout)

def create_media(filename, post_id):
	assert os.path.exists(filename), "media file not found"
	m = subprocess.run([WP_CLI, 'media', 'import', filename, '--post_id=' + str(post_id), '--preserve-filetime', '--porcelain', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
	assert m.returncode == 0, "Unable to import WordPress media"
	print("Created media ID %i" % (int(m.stdout)))
	return int(m.stdout)

def create_post(post):
	if post.caption == None:
		title = post.date_utc.isoformat()
	else:
		title = re.sub('\n$', '', post.caption)
	content = '[gallery link="file" size="large" columns="1"][playlist type=video]'

	while re.search('\s#\w+$', title) != None:
		title = re.sub('\s#\w+$', '', title)
		pass

	split = title.strip().partition('\n')
	title = split[0]
	content = split[2] + split[1] + content

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

	p = subprocess.run([WP_CLI, 'post', 'create', '--post_status=publish', '--post_author=' + str(user_id), '--post_title=' + title, '--post_content=' + content, '--post_category=' + str(category_id), '--post_date_gmt=' + post.date_utc.isoformat(), '--porcelain', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
	assert p.returncode == 0, "Unable to create WordPress post"
	post_id = int(p.stdout)
	print("Created post ID %i" % (post_id))

	for tag_id in post_tags:
		p = subprocess.run([WP_CLI, 'post', 'term', 'add', str(post_id), 'post_tag', str(tag_id), '--by=id', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
		assert p.returncode == 0, "Unable to set WordPress post tag"

	p = subprocess.run([WP_CLI, 'post', 'term', 'add', str(post_id), 'post_format', 'gallery', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
	assert p.returncode == 0, "Unable to set WordPress post format"

	p = subprocess.run([WP_CLI, 'post', 'meta', 'set', str(post_id), 'instagram_link', 'https://instagram.com/p/' + post.shortcode + '/', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
	assert p.returncode == 0, "Unable to set WordPress post meta"
	
	return post_id

def upload(post_id, url, extension, mime_type, date_utc):
	print("Downloading %s to %s/%i%s" % (url, DOWNLOAD_PATH, post_id, extension))
	if os.path.exists(DOWNLOAD_PATH + "/" + str(post_id) + extension):
		os.remove(DOWNLOAD_PATH + "/" + str(post_id) + extension)

	result = L.download_pic(filename=DOWNLOAD_PATH + "/" + str(post_id), url=url, mtime=date_utc)
	assert result == True, "Download failed"
	create_media(DOWNLOAD_PATH + "/" + str(post_id) + extension, post_id)
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

user = subprocess.run([WP_CLI, 'user', 'get', WORDPRESS_USER, '--format=json', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
assert user.returncode == 0, "Unable to find requested WordPress user"

user_id = int(json.loads(user.stdout)['ID'])
assert user_id != -1, "Unable to find requested WordPress category"
print("User ID: %i" % (user_id))

category = subprocess.run([WP_CLI, 'term', 'get', 'category', slugify(WORDPRESS_CATEGORY.lower()), '--by=slug', '--format=json', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
assert category.returncode == 0, "Unable to find requested WordPress category"

category_id = int(json.loads(category.stdout)['term_id'])
assert category_id != -1, "Unable to find requested WordPress category"
print("Category ID: %i" % (category_id))

posts = subprocess.run([WP_CLI, 'post', 'list', '--category=' + str(category_id), '--fields=post_date_gmt', '--posts_per_page=1', '--format=json', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
assert posts.returncode == 0, "Unable to fetch posts from WordPress"
latest_post_date = datetime.fromisoformat(json.loads(posts.stdout)[0]['post_date_gmt'] + "+00:00")
print("Most recent post in category: %s" % (latest_post_date))

t = subprocess.run([WP_CLI, 'term', 'list', 'post_tag', '--fields=term_id,slug', '--format=json', '--path=' + WORDPRESS_PATH], capture_output=True, text=True)
assert t.returncode == 0, "Unable to load tags from WordPress"
t = json.loads(t.stdout)
for tag in t:
	tags[tag['slug']] = tag['term_id']

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
