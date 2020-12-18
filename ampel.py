#!/usr/bin/env python3
import logging
import os
import shlex
import subprocess
import time

import cv2
import numpy
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from skimage.metrics import structural_similarity

def init_log(logfile):
	logging.basicConfig(format='[%(asctime)s] %(name)s %(levelname)s %(message)s', level=logging.INFO)
	if logfile:
		fd = os.open(logfile, os.O_WRONLY | os.O_APPEND | os.O_CREAT, mode=0o644)
		try:
			os.dup2(fd, 1)
			os.dup2(fd, 2)
		finally:
			os.close(fd)

def take_screenshots():
	options = webdriver.firefox.options.Options()
	options.headless = True
	driver = webdriver.Firefox(options=options)
	try:
		logging.info('loading Corona-Ampel...')
		driver.get('https://experience.arcgis.com/experience/d2386f3214c1451c81b242be69bb3d50')
		time.sleep(15)

		# find ampel tab-bar
		driver.switch_to.frame(driver.find_element_by_tag_name('iframe'))
		try:
			tabbar = driver.find_element_by_xpath('''
				//*[text()="Heute RKI"]
				/ancestor::
				*[contains(@class, "collapsed-bar-container")]
			''')
		finally:
			driver.switch_to.default_content()

		for _ in range(4):
			# get current caption
			driver.switch_to.frame(driver.find_element_by_tag_name('iframe'))
			try:
				caption = tabbar.find_element_by_xpath('./*[2]')
				caption = caption.get_attribute('textContent')
				caption = ' '.join(caption.split())
				filename = caption + '.png'
			finally:
				driver.switch_to.default_content()

			# take screenshot
			logging.info('taking screenshot of %r...', caption)
			yield (filename, driver.get_screenshot_as_png())

			# click arrow right
			driver.switch_to.frame(driver.find_element_by_tag_name('iframe'))
			try:
				right_btn = tabbar.find_element_by_xpath('./*[last()]')
				right_btn.click()
			finally:
				driver.switch_to.default_content()
	finally:
		driver.close()

def compare_images(old_name, new_data):
	if not os.path.isfile(old_name):
		return -1
	old_img = cv2.imread(old_name)
	new_img = numpy.frombuffer(new_data, dtype=numpy.uint8)
	new_img = cv2.imdecode(new_img, cv2.IMREAD_UNCHANGED)

	if new_img.shape != old_img.shape:
		return -1

	old_img = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
	new_img = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
	score, _ = structural_similarity(old_img, new_img, full=True)
	return score

def write_changed_images(imgs):
	for name, new_data in imgs:
		if new_data is None:
			logging.warning("skipping %s...", name)
			continue
		score = compare_images(name, new_data)
		logging.info("%s's SSIM: %s", name, score)
		if score < 0.99339:
			logging.info('%s changed', name)
			with open(name, 'wb') as fp:
				fp.write(new_data)

def run(*cmd):
	logging.info('running %s...', ' '.join(map(shlex.quote, cmd)))
	p = subprocess.run(cmd)
	return p.returncode == 0

if __name__ == '__main__':
	init_log(None)
	screenshots = dict(take_screenshots())
	write_changed_images(screenshots.items())
	now = time.strftime('%Y-%m-%d %H:%M %Z')
	run('git', 'add', '--', *screenshots.keys()) \
		and run('git', 'commit', '-m', 'updated screenshots ' + now) \
		and run('git', 'push')
