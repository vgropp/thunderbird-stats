#!/usr/bin/python3.6
import os, sys, time, json
from configparser import ConfigParser
from datetime import datetime
# pylint: disable=F0401
from tqdm import tqdm

# get config
cfg = ConfigParser()
cfg.read('config.ini')
# root directory of the maildir account directory of thunderbird
maildir = cfg.get('email', 'ThunderbirdAccountPath')
# own email address(es)
addresses = cfg.get('email', 'EmailAddresses').split(',')

def stats():
	""" read all mail files, collect and export data """
	mailfiles = []
	meta = { a: { 'in': 0, 'out': 0, 'total': 0, 'unread': 0 } for a in addresses }
	mails_per_year = { a: { 'in': {}, 'out': {} } for a in addresses }
	mails_per_month = { a: { 'in': {}, 'out': {} } for a in addresses }
	mails_per_hour = { a: { 'in': { i:0 for i in range(24) }, 'out': { i:0 for i in range(24) } } for a in addresses }
	mails_per_weekday = { a: { 'in': { i:0 for i in range(7) }, 'out': { i:0 for i in range(7) } } for a in addresses }
	mails_per_weekday_per_hour = { a: { 'in': { i:[0]*24 for i in range(7) }, 'out': { i:[0]*24 for i in range(7) } } for a in addresses }
	meta['total'] = { 'in': 0, 'out': 0, 'total': 0, 'unread': 0 }
	mails_per_year['total'] = { 'in': {}, 'out': {} }
	mails_per_month['total'] = { 'in': {}, 'out': {} }
	mails_per_hour['total'] = { 'in': { i:0 for i in range(24) }, 'out': { i:0 for i in range(24) } }
	mails_per_weekday['total'] = { 'in': { i:0 for i in range(7) }, 'out': { i:0 for i in range(7) } }
	mails_per_weekday_per_hour['total'] = { 'in': { i:[0]*24 for i in range(7) }, 'out': { i:[0]*24 for i in range(7) } }
	# check configured mail directory
	if not os.path.exists(maildir):
		print('Error: The configured mail directory doesn\' exist:')
		print(maildir)
		print('Please set the corresponding path in config.ini > ThunderbirdAccountPath')
		return False
	# get all mail files
	for root,_,files in os.walk(maildir):
		for f in files:
			_,file_extension = os.path.splitext(f)
			# get directory information: unread mails count
			if file_extension == '.msf':
				for line in reversed(list(open(os.path.join(root, f), 'r', encoding='latin1'))):
					if '[1:^9F(^A2=' in line:
						start = line.find('A2=')+3
						end = line.find(')]', start)
						meta['total']['unread'] += int(line[start:end], 16)
						break
			else:
				mailfiles.append(os.path.join(root, f))

	# process all mail files to get data
	for f in tqdm(mailfiles, unit='mails', mininterval=0.05):
		mailtype = None
		maildate = None
		email = { 'in': '', 'out': '' }
		for line in open(f, 'r', encoding='latin1'):
			# determine wether an email was sent or received
			if line.lower().startswith('from:'):
				mailtype = 'out' if any(a in line for a in addresses) else 'in'
				for a in addresses:
					if a in line:
						email['out'] = a
						break
				continue
			if line.lower().startswith('to:'):
				for a in addresses:
					if a in line:
						email['in'] = a
						break
				continue
			# get mail date
			if line.startswith('Date:'):
				startindex = line.index(',')+2 if ',' in line else line.index(' ')+1
				datestring = line[startindex:].strip()
				datestring = datestring[:datestring.rindex("+")+5] if '+' in datestring else datestring
				try:
					maildate = time.strptime(datestring, '%d %b %Y %H:%M:%S %z')
				except ValueError:
					try:
						datestring = datestring[:datestring.rindex(":")+3]
						maildate = time.strptime(datestring, '%d %b %Y %H:%M:%S')
					except ValueError:
						try:
							maildate = time.strptime(datestring, '%d %b %Y %H:%M')
						except ValueError:
							maildate = None
			# if maildate was not found, try alternative approache/formats
			if maildate is None and ' +0000' in line and len(line)>26:
				datestring = line[line.index(' +0000')-20:line.index(' +0000')+6]
				try:
					maildate = time.strptime(datestring, '%d %b %Y %H:%M:%S %z')
				except ValueError:
					datestring = line[8:26]
					try:
						maildate = time.strptime(datestring, '%Y-%m-%d %H:%M:%S')
					except ValueError:
						datestring = line[6:26]
						try:
							maildate = time.strptime(datestring, '%d %b %Y %H:%M:%S')
						except ValueError:
							maildate = None
			# save found data
			if mailtype is not None and maildate is not None:
				# build meta data
				meta['total'][mailtype] += 1
				meta['total']['total'] += 1
				if 'oldest' not in meta['total']:
					meta['total']['oldest'] = maildate
				if 'newest' not in meta['total']:
					meta['total']['newest'] = maildate
				meta['total']['oldest'] = maildate if maildate < meta['total']['oldest'] else meta['total']['oldest']
				meta['total']['newest'] = maildate if maildate >= meta['total']['newest'] else meta['total']['newest']
				# build mails per year and per month
				if maildate.tm_year in mails_per_year['total'][mailtype]:
					mails_per_year['total'][mailtype][maildate.tm_year] += 1
					mails_per_month['total'][mailtype][maildate.tm_year][maildate.tm_mon] += 1
				else:
					mails_per_year['total'][mailtype][maildate.tm_year] = 1
					mails_per_month['total'][mailtype][maildate.tm_year] = { i:0 for i in range(1,13) }
					mails_per_month['total'][mailtype][maildate.tm_year][maildate.tm_mon] = 1
				# build number of mails per hour
				mails_per_hour['total'][mailtype][maildate.tm_hour] += 1
				# build number of mails per weekday
				mails_per_weekday['total'][mailtype][maildate.tm_wday] += 1
				# build number of mails per weekday per hour
				mails_per_weekday_per_hour['total'][mailtype][maildate.tm_wday][maildate.tm_hour] += 1
				if email[mailtype] != '':
					# build meta data
					meta[email[mailtype]][mailtype] += 1
					meta[email[mailtype]]['total'] += 1
					if 'oldest' not in meta[email[mailtype]]:
						meta[email[mailtype]]['oldest'] = maildate
					if 'newest' not in meta[email[mailtype]]:
						meta[email[mailtype]]['newest'] = maildate
					meta[email[mailtype]]['oldest'] = maildate if maildate < meta[email[mailtype]]['oldest'] else meta[email[mailtype]]['oldest']
					meta[email[mailtype]]['newest'] = maildate if maildate >= meta[email[mailtype]]['newest'] else meta[email[mailtype]]['newest']
					# build mails per year and per month
					if maildate.tm_year in mails_per_year[email[mailtype]][mailtype]:
						mails_per_year[email[mailtype]][mailtype][maildate.tm_year] += 1
						mails_per_month[email[mailtype]][mailtype][maildate.tm_year][maildate.tm_mon] += 1
					else:
						mails_per_year[email[mailtype]][mailtype][maildate.tm_year] = 1
						mails_per_month[email[mailtype]][mailtype][maildate.tm_year] = { i:0 for i in range(1,13) }
						mails_per_month[email[mailtype]][mailtype][maildate.tm_year][maildate.tm_mon] = 1
					# build number of mails per hour
					mails_per_hour[email[mailtype]][mailtype][maildate.tm_hour] += 1
					# build number of mails per weekday
					mails_per_weekday[email[mailtype]][mailtype][maildate.tm_wday] += 1
					# build number of mails per weekday per hour
					mails_per_weekday_per_hour[email[mailtype]][mailtype][maildate.tm_wday][maildate.tm_hour] += 1
					# stop and jump to next file
					break
				break
		# for debugging purposes:
		# else:
		# 	if mailtype is None or maildate is None:
		# 		fh = open('./src/data/debug.txt', 'a')
		# 		fh.write(open(f, 'r', encoding='latin1').read())
		# 		fh.close

	# export data
	if not os.path.exists('./src/data/'):
		os.makedirs('./src/data/')
	with open('./src/data/mails-per-year.json', 'w') as f:
		json.dump(mails_per_year, f)
	with open('./src/data/mails-per-month.json', 'w') as f:
		json.dump(mails_per_month, f)
	with open('./src/data/mails-per-hour.json', 'w') as f:
		json.dump(mails_per_hour, f)
	with open('./src/data/mails-per-weekday.json', 'w') as f:
		json.dump(mails_per_weekday, f)
	with open('./src/data/mails-per-weekday-per-hour.json', 'w') as f:
		json.dump(mails_per_weekday_per_hour, f)
	with open('./src/data/meta.json', 'w') as f:
		# build featured and meta data
		meta['total']['days'] = (time.mktime(meta['total']['newest']) - time.mktime(meta['total']['oldest']))/(60*60*24)
		meta['total']['weeks'] = meta['total']['days']/7
		meta['total']['months'] = meta['total']['days']/(365/12)
		meta['total']['years'] = meta['total']['days']/365
		meta['total']['oldest'] = time.strftime("%Y-%m-%dT%H:%M:%S", meta['total']['oldest'])
		meta['total']['newest'] = time.strftime("%Y-%m-%dT%H:%M:%S", meta['total']['newest'])
		meta['total']['tstamp'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
		for a in addresses:
			meta[a]['days'] = (time.mktime(meta[a]['newest']) - time.mktime(meta[a]['oldest']))/(60*60*24)
			meta[a]['weeks'] = meta[a]['days']/7
			meta[a]['months'] = meta[a]['days']/(365/12)
			meta[a]['years'] = meta[a]['days']/365
			meta[a]['oldest'] = time.strftime("%Y-%m-%dT%H:%M:%S", meta[a]['oldest'])
			meta[a]['newest'] = time.strftime("%Y-%m-%dT%H:%M:%S", meta[a]['newest'])
			meta[a]['tstamp'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
		json.dump(meta, f, default=json_datetime)

	return True


def json_datetime(obj):
	"""JSON serializer for datetime objects"""
	if isinstance(obj, (datetime)):
		return obj.isoformat()
	raise TypeError ("Type %s not serializable" % type(obj))


# output
print('Processing mails...')
if stats():
	print('Finished.')
