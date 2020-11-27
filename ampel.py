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

def click_week(driver):
	try:
		btn = driver.find_element_by_xpath('//*[text()="Wochenverlauf")]')
		btn.click()
		return
	except NoSuchElementException:
		pass
	for iframe in driver.find_elements_by_tag_name('iframe'):
		driver.switch_to.frame(iframe)
		try:
			click_week(driver)
		finally:
			driver.switch_to.parent_frame()

def take_screenshots():
	options = webdriver.firefox.options.Options()
	options.headless = True
	driver = webdriver.Firefox(options=options)
	try:
		logging.info('loading Corona-Ampel...')
		driver.get('https://www.dresden.de/de/leben/gesundheit/hygiene/infektionsschutz/corona.php')
		ampel = driver.find_element_by_xpath('//*[text()="Fallzahlen (Dashboards)"]')
		ampel.click()
		ampel = ampel.find_element_by_xpath('../../..//iframe')

		time.sleep(15)
		logging.info("taking screenshot of today's incidence...")
		day = ampel.screenshot_as_png

		week = None
		try:
			driver.switch_to.frame(ampel)
			click_week(driver)

			driver.switch_to.default_content()
			logging.info("taking screenshot of week's incidence...")
			week = ampel.screenshot_as_png
		except:
			logging.exception("cannot take screenshot of week's incidence")
	finally:
		driver.close()
	return (day, week)

def compare_images(old_name, new_data):
	try:
		old_img = cv2.imread(old_name)
	except FileNotFoundError:
		return -1
	new_img = numpy.frombuffer(new_data, dtype=numpy.uint8)
	new_img = cv2.imdecode(new_img, cv2.IMREAD_UNCHANGED)

	old_img = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
	new_img = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
	score, _ = structural_similarity(old_img, new_img, full=True)
	return score

def write_changed_images(*imgs):
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
	imgs = ('inzidenz.png', '7-tage.png')
	screenshots = take_screenshots()
	write_changed_images(*zip(imgs, screenshots))
	now = time.strftime('%Y-%m-%d %H:%M %Z')
	run('git', 'add', '--', *imgs) \
		and run('git', 'commit', '-m', 'updated screenshots ' + now) \
		and run('git', 'push')
