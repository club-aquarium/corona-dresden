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
		driver.get('https://stva-dd.maps.arcgis.com/apps/opsdashboard/index.html#/903c42db63184099a4da5e23c4e732b3')
		time.sleep(15)

		# find active tab
		tab = driver.find_element_by_xpath('//*[contains(@class, "is-active")]')

		for _ in range(4):
			# get current caption
			caption = tab.get_attribute('textContent')
			caption = ' '.join(caption.split())
			filename = caption + '.png'

			# take screenshot
			logging.info('taking screenshot of %r...', caption)
			yield (filename, driver.get_screenshot_as_png())

			# next tab
			try:
				tab = tab.find_element_by_xpath('./following-sibling::*')
			except NoSuchElementException:
				break
			tab.click()
	finally:
		driver.close()

def compare_images(old_name, new_data):
	if not os.path.isfile(old_name):
		return -1
	old_img = cv2.imread(old_name)
	new_img = numpy.frombuffer(new_data, dtype=numpy.uint8)
	new_img = cv2.imdecode(new_img, cv2.IMREAD_UNCHANGED)

	old_img = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
	new_img = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)

	if new_img.shape != old_img.shape:
		return -1

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
	run('git', 'commit', '-m', 'updated screenshots ' + now, '--', *screenshots.keys()) \
		and run('git', 'push')
