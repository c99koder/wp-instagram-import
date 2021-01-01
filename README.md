# WP-Instagram-Import
Import Instagram posts into WordPress

## Configuration
Image uploading requires installing the following WordPress plugin for API authentication: https://github.com/WP-API/Basic-Auth
The following WordPress plugin is also recommended for creating application-specific passwords: https://wordpress.org/plugins/application-passwords/

Open the Python script and set your credentials and configuration at the top of the file

 * __INSTAGRAM_PROFILE__: Your Instagram profile username (must be a public profile)
 * __WORDPRESS_URL__: The URL to your WordPress site
 * __WORDPRESS_USER__: The WordPress username that will be creating the posts
 * __WORDPRESS_PASS__: Password for the WordPress account (create an application password above for security)
 * __WORDPRESS_CATEGORY__: The category that will be used for the posts (must already exist)
 * __DOWNLOAD_PATH__: Temporary location for storing images/videos during upload

## Usage
Check your Python version and make sure version 3.7 or newer is installed on your system:
```
$ python3 --version
```

Install required python3 modules:
```
$ pip3 install requests instaloader wordpress-api awesome-slugify
```

Run the Python script from the terminal and it will import any photos or videos from Instagram that are more recent than the last post in the __WORDPRESS_CATEGORY__

# License

Copyright (C) 2021 Sam Steele. Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
