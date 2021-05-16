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
from selenium.webdriver.support.ui import WebDriverWait
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

def resize_window(driver):
	W, H = 960, 720

	widget = driver.find_element_by_css_selector('.widget')

	w = int(widget.get_attribute('offsetWidth'),  10)
	h = int(widget.get_attribute('offsetHeight'), 10)
	dw = W - w
	dh = H - h
	x = driver.get_window_size()
	driver.set_window_size(x['width'] + dw, x['height'] + dh)

	while True:
		w = int(widget.get_attribute('offsetWidth'),  10)
		h = int(widget.get_attribute('offsetHeight'), 10)
		if (w, h) == (W, H):
			break
		dw = 1 if w < W else -1
		dh = 1 if h < H else -1
		x = driver.get_window_size()
		driver.set_window_size(x['width'] + dw, x['height'] + dh)

def extract_widgets():
	options = webdriver.firefox.options.Options()
	options.headless = True
	driver = webdriver.Firefox(options=options)
	try:
		logging.info('loading Corona-Ampel...')
		driver.get('https://stva-dd.maps.arcgis.com/apps/opsdashboard/index.html#/903c42db63184099a4da5e23c4e732b3')
		# when the SVG contains text it should be loaded
		# wait a second to be sure
		WebDriverWait(driver, 30).until(lambda d: (
			d.find_element_by_tag_name('svg').find_element_by_tag_name('text'),
			time.sleep(1),
		))
		resize_window(driver)

		# find active tab
		tab = driver.find_element_by_css_selector('.is-active')

		for _ in range(4):
			# get current caption
			caption = tab.get_attribute('textContent')
			caption = ' '.join(caption.split())
			filename = caption + '.html'

			driver.execute_script('''
				(({style, offsetWidth, offsetHeight}) => {
					style.width  = offsetWidth  + "px";
					style.height = offsetHeight + "px";
				})(document.querySelector(".widget"));
			''')
			html = driver.find_element_by_css_selector('.widget')
			html = html.get_attribute('outerHTML')
			yield (filename, html)

			# next tab
			try:
				tab = tab.find_element_by_xpath('./following-sibling::*')
			except NoSuchElementException:
				break
			tab.click()
			time.sleep(0.5)
	finally:
		driver.close()

def write_html(htmls):
	index_html = '''<!DOCTYPE html>
<html>
	<head>
		<meta charset="UTF-8"/>
		<style>
			body {
				min-width: 960px;
				margin: 0 auto;
				background: #222;
				color: #fff;
				font-family: sans-serif;
			}
		</style>
	</head>
	<body>
'''
	for name, html in htmls:
		index_html += '<h1>' + name[:-5].replace('&', '&amp;').replace('<', '&lt;') + '</h1>'
		index_html += html
		with open(name, 'w', encoding='utf-8') as fp:
			fp.write('''<!DOCTYPE html>
<html>
	<head>
		<meta charset="UTF-8"/>
	</head>
	<body style="background: #222; margin: 0; font-family: sans-serif;">
''' + html + '''
	</body>
</html>
''')
	index_html += '''
	</body>
</html>
'''
	with open('index.html', 'w', encoding='utf-8') as fp:
		fp.write(index_html)

def run(*cmd):
	logging.info('running %s...', ' '.join(map(shlex.quote, cmd)))
	p = subprocess.run(cmd)
	return p.returncode == 0

if __name__ == '__main__':
	init_log(None)
	widgets = dict(extract_widgets())
	write_html(widgets.items())
	now = time.strftime('%Y-%m-%d %H:%M %Z')
	run('git', 'add', '--', 'index.html', *widgets.keys()) \
		and run('git', 'commit', '-m', 'updated screenshots ' + now) \
		and run('git', 'push')
