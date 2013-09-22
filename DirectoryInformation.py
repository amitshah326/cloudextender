from .api import fs
#import fs
import os
import os.path
import stat
import datetime
import shutil
import urllib,urllib2,requests
import json
import yaml
import dateutil

class FileInformation(fs.FileInformation):
	authorization = None
	folderid = None
	filename = None
	fileid = None

	def __init__(self, fullPath, lastModified, size, parent, authorization, folderid, fileid, containerid):
		super(FileInformation, self).__init__(fullPath, lastModified, size, parent)
		self.authorization = authorization
		self.filename = self.name
		self.folderid = folderid
		self.fileid = fileid
		self.containerid = containerid

	def download(self):
		"""
		Download a file and return a file-like object of its contents
		"""
		paras = {
			'folderid': self.folderid,
			'filename': self.filename.encode('utf-8'),
			'fileid': self.fileid.encode('utf-8'),
			'containerid': self.containerid.encode('utf-8')
		}
		paras = urllib.urlencode(paras)
		reque = urllib2.Request(
			"https://api.point.io/v2/folders/files/download.json?"+paras,
			headers={
				'Authorization': self.authorization,
			})
		req = urllib2.urlopen(reque)
		res = req.readlines()
		res = json.loads(res[0])
		resURL = res['RESULT']
		resFile = urllib.urlopen(resURL)
		return resFile
		#example: result = cld.DownloadFile(cld.sessionkey, r"64B367EA-286D-481F-92DD9E28E9B3B4C1", "JustATest.txt", "10529642791")

	def upload(self, file):
		files = {'filecontents': file}
		#folderid = folderidVal
		#filename = filenamjson.loads
		# newfileid = self.filename
		# CAUTION: filename will not change to be the uploaded file name
		filecontents = files
		data = {
			'folderid': self.folderid,
			'filename': self.filename,
			# if filename is different, a new file will be uploaded
			'fileid': self.fileid,
			'containerid': self.containerid,
			#'filecontents': filecontents
		}
		req = requests.post(
			"https://api.point.io/v2/folders/files/upload.json",
			headers= {'Authorization': self.authorization},
			files = files,
			data = data
		)

		res = req.json()
		# error exception
		# update lastModified
		rawTime = res['INFO']['DETAILS']['RESULT']['MODIFIED']
		time = rawTime.split("'")[1]
		self.lastModified = dateutil.parser.parse(time + " GMT")
		# update size
		self.size = res['INFO']['DETAILS']['RESULT']['SIZE']
		# CAUTION: fileID might not be correct after upload! leave it to DirInfo class
		# no further upload or delete!

	def delete(self):
		paras = {
			'folderid': self.folderid,
			'filename': self.filename.encode('utf-8'),
			'fileid': self.fileid.encode('utf-8'),
			'containerid': self.containerid.encode('utf-8')
		}
		paras = urllib.urlencode(paras)
		reque = urllib2.Request(
			"https://api.point.io/v2/folders/files/delete.json?"+paras,
			headers={
				'Authorization': self.authorization,
			})
		req = urllib2.urlopen(reque)

class DirectoryInformation(fs.DirectoryInformation):
	url_list = 'https://api.point.io/v2/folders/list.json'
	url_create = 'https://api.point.io/v2/folders/create.json'
	def __init__(self, folderid, authorization, path, parent = None, lastModified = None, size = None, containerid = None):
		super(DirectoryInformation, self).__init__(path, lastModified, size, parent) 

		self.folderid = folderid
		self.authorization = authorization
		self.containerid = containerid
		

	def getFiles(self):
		query_args = { 'folderId':self.folderid.encode('utf-8'), 'containerid': self.containerid.encode('utf-8')  }
		data = urllib.urlencode(query_args)
		request = urllib2.Request(self.url_list, data, 
			headers = {
				"Authorization": self.authorization
			})
		response = urllib2.urlopen(request)
		r = response.readline()
		py = json.loads(r)

		for item in py["RESULT"]["DATA"]:
			if (item[2] != "DIR"):
				fullPath = item[4] + item[1]
				t = item[7].split("'")[1]
				lastModified = t + " GMT"
				size = item[8]
				# fileid = item[0]
				fileid = unicode(int(item[0]) if isinstance(item[0], float) else item[0])
				yield FileInformation(fullPath, lastModified, size, self, self.authorization, self.folderid, fileid, self.containerid)

	def getDirectories(self):
		query_args = { 'folderId': self.folderid.encode('utf-8'), 'containerid': self.containerid.encode('utf-8') }
		data = urllib.urlencode(query_args)
		request = urllib2.Request(self.url_list, data, 
			headers = {
				"Authorization": self.authorization
			})
		response = urllib2.urlopen(request)
		r = response.readline()
		py = json.loads(r)
		# folderid, authorization, parent
		for item in py["RESULT"]["DATA"]:
			if (item[2] == "DIR"):
				path = item[1]
				fullPath = item[4] + item[1]
				t = item[7].split("'")[1]
				lastModified = t + " GMT"
				size = item[8]
				# fileid = item[0]
				fileid = unicode(int(item[0]) if isinstance(item[0], float) else item[0])
				containerid = unicode(int(item[3]) if isinstance(item[3], float) else item[3])
				yield DirectoryInformation(self.folderid, self.authorization, fullPath, self, lastModified, size, containerid)

	def createDirectory(self, name):
		query_args = { 'folderId':self.folderid.encode('utf-8'), 'foldername':name.encode('utf-8') }
		data = urllib.urlencode(query_args)
		request = urllib2.Request(self.url_create, data, 
			headers = {
				"Authorization": self.authorization
			})
		response = urllib2.urlopen(request)
		path = self.fullPath + "/" + name
		# list the files
		query_args = { 'folderId':self.folderid.encode('utf-8') }
		data = urllib.urlencode(query_args)
		request = urllib2.Request(self.url_list, data, 
			headers = {
				"Authorization": self.authorization
			})
		response = urllib2.urlopen(request)
		r = response.readline()
		py = json.loads(r)
		for item in py["RESULT"]["DATA"]:
			if (item[1] == name):
				containerid = unicode(int(item[3]) if isinstance(item[3], float) else item[3])
		#Get lastMod and size from response
		return DirectoryInformation(self.folderid, self.authorization, path, self, None, None, containerid)		

	def createFile(self, name, file):
		fnFull = os.path.join(self.fullPath, name)		
		newFile = FileInformation(fnFull, "", 0, self.parent, self.authorization, self.folderid, name, self.containerid)
		newFile.upload(file);
		# CAUTION: fileid might not correct now!
		# remaining: grab the fileid
		fileList = self.getFiles()
		for item in fileList:
			if (item.filename == name):
				newFile.fileid = item.fileid
		return newFile

class FileSystem(fs.FileSystem):
	rootDir = '/'
	folderid = None
	authorization = None
	def __init__(self, folderid, authorization):
		self.folderid = folderid
		self.authorization = authorization
	def getRoot(self):
		return DirectoryInformation(self.folderid, self.authorization, self.rootDir, None, None, None, '')
