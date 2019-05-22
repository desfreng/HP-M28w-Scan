#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from Scanner import Scanner
from os import system

scan = Scanner("192.168.1.11")

scan.scan_request(0, 0, scan.max_size[0], scan.max_size[1], scan.scan_format[0], 200, 200, scan.color_modes[0])

while not scan.job_ended:
	# system('clear')
	print("Job Age : " + str(scan.job_age))

save = scan.get_file()
