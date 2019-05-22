#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as Et
import requests
import re


class Scanner:
	def __init__(self, ip):
		self._url = "http://" + ip + ":8080/eSCL/"
		self._ns = {"scan": "http://schemas.hp.com/imaging/escl/2011/05/03",
		            "pwg": "http://www.pwg.org/schemas/2010/12/sm"}
		self._col_mod = []
		self._res = []
		self._doc_frm = []
		self._max_size = ()
		self._min_size = ()
		self._update_capacity()

		self._job_id = None
		self._job_dl = None

	@property
	def job_age(self):
		if self._job_id is None:
			return 0

		r = requests.get(self._url + "ScannerStatus")
		xml_result = Et.fromstring(r.text)

		for a in xml_result.findall(".//scan:JobInfo", self._ns):
			if a.find("pwg:JobUuid", self._ns).text == self._job_id:
				return int(a.find("scan:Age", self._ns).text)

	@property
	def job_ended(self):
		if self._job_id is None:
			return False

		r = requests.get(self._url + "ScannerStatus")
		xml_result = Et.fromstring(r.text)

		for a in xml_result.findall(".//scan:JobInfo", self._ns):
			if a.find("pwg:JobUuid", self._ns).text == self._job_id:
				return int(a.find("pwg:ImagesToTransfer", self._ns).text) > 0
		return False

	def _update_capacity(self):
		r = requests.get(self._url + "ScannerCapabilities")
		xml_result = Et.fromstring(r.text)

		self._col_mod.clear()
		for a in xml_result.findall(".//scan:ColorMode", self._ns):
			self._col_mod.append(a.text)

		self._res.clear()
		for a in xml_result.findall(".//scan:DiscreteResolution", self._ns):
			x_res = int(a.find("scan:XResolution", self._ns).text)
			y_res = int(a.find("scan:YResolution", self._ns).text)
			self._res.append((x_res, y_res))

		self._doc_frm.clear()
		for a in xml_result.findall(".//scan:DocumentFormatExt", self._ns):
			self._doc_frm.append(a.text)

		min_x = int(xml_result.find(".//scan:MinWidth", self._ns).text)
		min_y = int(xml_result.find(".//scan:MinHeight", self._ns).text)
		self._min_size = (min_x, min_y)

		max_x = int(xml_result.find(".//scan:MaxWidth", self._ns).text)
		max_y = int(xml_result.find(".//scan:MaxHeight", self._ns).text)
		self._max_size = (max_x, max_y)

	def scanning(self):
		return self.state == "Processing"

	def idle(self):
		return self.state == "Idle"

	@property
	def state(self):
		r = requests.get(self._url + "ScannerStatus")
		status_xml = Et.fromstring(r.text)
		return status_xml.find(".//pwg:State", self._ns).text

	@property
	def color_modes(self):
		return self._col_mod

	@property
	def resolutions(self):
		return self._res

	@property
	def scan_format(self):
		return self._doc_frm

	@property
	def max_size(self):
		return self._max_size

	@property
	def min_size(self):
		return self.min_size

	def scan_request(self, x, y, width, height, doc_format, x_res, y_res, color_mode):
		command = """<?xml version='1.0' encoding='utf-8'?>
		<escl:ScanSettings xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm" xmlns:escl="http://schemas.hp.com/imaging/escl/2011/05/03">
			<pwg:Version>2.63</pwg:Version>
			<pwg:ScanRegions pwg:MustHonor="false">
				<pwg:ScanRegion>
					<pwg:ContentRegionUnits>escl:ThreeHundredthsOfInches</pwg:ContentRegionUnits>
					<pwg:XOffset>{}</pwg:XOffset>
					<pwg:YOffset>{}</pwg:YOffset>
					<pwg:Width>{}</pwg:Width>
					<pwg:Height>{}</pwg:Height>
				</pwg:ScanRegion>
			</pwg:ScanRegions>
			<escl:DocumentFormatExt>{}</escl:DocumentFormatExt>
			<pwg:InputSource>Platen</pwg:InputSource>
			<escl:XResolution>{}</escl:XResolution>
			<escl:YResolution>{}</escl:YResolution>
			<escl:ColorMode>{}</escl:ColorMode>
		</escl:ScanSettings>""".format(x, y, width, height, doc_format, x_res, y_res, color_mode)

		r = requests.post(self._url + "ScanJobs", data=command.encode(), headers={'content-type': 'text/xml'})

		if r.status_code == 201:
			self._job_id = re.search(r"http://.*:80/eSCL/ScanJobs/([a-z0-9-]*)", r.headers['Location']).group(1)
			self._job_dl = r.headers['Location'] + "/NextDocument"
		else:
			raise Exception("Scanner Unavailable")

	def get_file(self):
		if not self.job_ended:
			return

		r = requests.get(self._job_dl)
		self._job_id = None
		self._job_dl = None

		return bytes(r.content)
