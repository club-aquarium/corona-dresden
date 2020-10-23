#!/usr/bin/env python3
import logging
import os
import shlex
import subprocess
import time

from selenium import webdriver

def init_log(logfile):
	logging.basicConfig(format='[%(asctime)s] %(name)s %(levelname)s %(message)s', level=logging.INFO)
	if logfile:
		fd = os.open(logfile, os.O_WRONLY | os.O_APPEND | os.O_CREAT, mode=0o644)
		try:
			os.dup2(fd, 1)
			os.dup2(fd, 2)
		finally:
			os.close(fd)

def take_screenshots(day, week):
	options = webdriver.firefox.options.Options()
	options.headless = True
	driver = webdriver.Firefox(options=options)
	try:
		logging.info('loading Corona-Ampel...')
		driver.get('https://www.dresden.de/de/leben/gesundheit/hygiene/infektionsschutz/corona.php')
		ampel = driver.find_element_by_xpath('//*[text()="Fallzahlen (Corona-Ampel)"]')
		ampel.click()
		ampel = ampel.find_element_by_xpath('../../..//iframe')

		time.sleep(15)
		logging.info('taking screenshot %r...', day)
		ampel.screenshot(day)

		driver.switch_to.frame(ampel)
		inzidenz = driver.find_element_by_xpath('//*[text()="7-Tage-Inzidenz"]')
		inzidenz.click()

		driver.switch_to.default_content()
		logging.info('taking screenshot %r...', week)
		ampel.screenshot(week)
	finally:
		driver.close()

def run(*cmd):
	logging.info('running %s...', ' '.join(map(shlex.quote, cmd)))
	p = subprocess.run(cmd)
	return p.returncode == 0

if __name__ == '__main__':
	imgs = ('inzidenz.png', '7-tage.png')
	init_log(None)
	take_screenshots(*imgs)
	now = time.strftime('%Y-%m-%d %H:%M %Z')
	run('git', 'add', '--', *imgs) \
		and run('git', 'commit', '-m', 'updated screenshots ' + now) \
		and run('git', 'push')
