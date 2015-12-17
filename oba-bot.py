#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import cookielib
import mechanize
import urllib
import urllib2
from bs4 import BeautifulSoup
from pymongo import MongoClient

# Database stuff - JBG
client = MongoClient()
db = client.library
collection = db.books
name_collection = db.names

# File to write to - JBG
txt_file = open('library.txt', 'w')

# Library url - JBG
url = 'http://zoeken.oba.nl'

br = mechanize.Browser()
br.addheaders = [
  ('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:40.0) Gecko/20100101 Firefox/40.0'),
  ('Accept', '*/*'),
  ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'),
  ('Accept-Language', 'en-US,en;q=0.5'),
  ('Connection', 'keep-alive')
]

# Enable cookie support for urllib2 
cookiejar = cookielib.LWPCookieJar()
br.set_cookiejar(cookiejar)

# Browser options
br.set_handle_equiv(True)
br.set_handle_gzip(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)

def get_gender(name):
  name = name.encode('utf8') 
  cur = name_collection.find({'name': name})
  if cur.count() > 0:
    print('WOOHOO found name in database!!!')
    gender = cur[0]['gender']
    if gender == None:
      return 'unknown'.encode('utf8')
    else:
      return gender.encode('utf8') 
  else:
    try:
      gender_req = urllib2.urlopen('https://api.genderize.io/?name=' + name)
      data = json.load(gender_req)
      # Add it to the database so we don't make multiple requests for names we already know - JBG
      name_collection.insert_one(data)
      gender = data['gender']
      if gender == None:
        return 'unknown'.encode('utf8') 
      else:
        return gender.encode('utf8') 
    except Exception, e:
      # We can only make 1000 gender requests per day... - JBG
      print(e)
      exit()

def get_text(child):
  try:
    link = child.find('a')
    return link.contents[0].strip()
  except Exception, e:
    try:
      return child.contents[0].strip()
    except Exception, e:
      return None

count = 0
a = 97 # is a - JBG

# HACK: This is starting a b again - JBG
for i in range(19, 26):
  page = 1 
  q = str(unichr(a+i))
  print 'q: ' + q 
  # HACK: Current page - JBG
  j = 16
  page_count = 9999 
  while j < page_count:
    print 'j: ' + str(j) + ', page_count: ' + str(page_count)
    query_url = url + '?curpage=' + str(j) + '&q=' + q + '&dim=dcterms:type.uri%28http://dbpedia.org/ontology/Book%29'
    print query_url
    try:
      res = br.open(query_url)
      soup = BeautifulSoup(res.read(), 'html.parser')
      articles = soup.findAll('article', class_='record')

      # Check number of pages - JBG
      pages = soup.find('div', class_='pagination')
      pages_list = pages.findAll('a')
      returned_page_count = pages_list[len(pages_list) - 3].contents[0]

      if int(returned_page_count) != page_count:
        page_count = int(returned_page_count)
        print 'PAGE_COUNT: ' + str(page_count)

      for article in articles:
        try:
          subpath = article.findAll('a', class_='classiclink')[0]['href']
          link = url + subpath
          try:
            #print link
            res = br.open(link)
            soup = BeautifulSoup(res.read(), 'html.parser')
            article = soup.findAll('article', class_='fullrecord-block')[0]
            details = article.find('dl')
            children = details.findChildren()
            key = None 
            book_dict = {}

            authors_str = ''
            authors = soup.findAll('a', class_='author') #[0].contents[0]
            for author in authors:
              authors_str += author.contents[0] + ','
            book_dict['author'] = authors_str
      
            # Get the genders - JBG
            author_names = authors_str.split(',')
            book_gender = 'unknown'
            for author_name in author_names:
              first_name = author_name.split(' ')[0]
              first_name = first_name.replace('.', '')
              gender = get_gender(first_name.lower())
              if book_gender == 'unknown':
                book_gender = gender
              elif book_gender != gender and gender != 'unknown':
                book_gender = 'both'
            print('BOOK GENDER IS: ' + book_gender.encode('utf8'))
            book_dict['gender'] = book_gender

            for child in children:
              if child.name == 'dt':
                text = get_text(child)
                if text != None:
                  key = text
              elif child.name == 'dd':
                text = get_text(child)
                if text != None and key != None:
                  book_dict[key] = text
                elif text != None and key == None:
                  obj = book_dict[key]
                  if isinstance(obj, list):
                    obj.append(text)
                  else:
                    obj = [ obj ]
                    obj.append(text)
                    book_dict[key] = obj 
          
            # Write to File - JBG
            json_str = json.dumps(book_dict, separators=(',',':'))
            txt_file.write(json_str)
            txt_file.write('\n') 
            print json_str

            # Write to DB - JBG
            collection.insert_one(book_dict)

            count += 1
            print 'Inserted ' + str(count) + ' books.'
          except Exception, e:
            print e 
        except Exception, e:
          print e 
    except Exception, e:
      #print e.code
      print e
      #print e.read()
    j += 1
# Close database - JBG
client.close()

# Close text file - JBG
txt_file.close()

#res = br.open(url)

#print br.title()
#print res.info()  # headers
#print res.read()  # body

