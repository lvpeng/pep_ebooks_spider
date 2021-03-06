# -*- coding:utf-8 -*-
import requests
from bs4 import BeautifulSoup
import lxml
import os, sys, json
from pathlib import Path
from threading import Thread
import queue


url = 'https://bp.pep.com.cn/jc/'

res = requests.get(url)
res.encoding = 'utf-8'
req_url = res.url
books_counts=0
books_downloaded_count=0
## response:
##   content-type: text/html

''' [
    {
    "container_title": "义务教育教科书（小学）",
    "subjects": [
        {
            "name": "小学道德与法治教科书",
            "rlative_url": "./ywjygjkcjc/xdjc/",
            "books": [
                {
                "name": "道德与法治一年级下册",
                "dwn_url": "./202001/P020200219781109508538.pdf"
                },
                {
                "name": "道德与法治二年级下册",
                "dwn_url": "./202001/P020200219781109508538.pdf"
                }
            ]
        },
        {
            "name": "小学道德与法治教师教学用书",
            "rlative_url": "./ywjygjkcjc/xxdfjsys/"
        },
        ]
    }
    
] '''
    
data = {}
data['books']=[]

def getEbooksRequest(url, book_dir, grade_stage, subject_name):
    global books_counts
    ebooks_url = os.path.join(req_url, url )
    print('Request {0}/{1} book'.format(grade_stage, subject_name))
    response= requests.get(ebooks_url)
    response.encoding='utf-8'
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        #print('Success & Close Connection')
        response.close()   
        book_nodes = soup.find_all("li", class_="fl js_cp")
        
        books_counts += len(book_nodes)
        # book name
        for _book in book_nodes:
            book = {}
            
            _book_name = _book.select('h6')[0].text
            _book_dow_url = _book.select('a.btn_type_dl')[0]['href']
            _book_dow_fullurl = os.path.join(ebooks_url, _book_dow_url)
            book['name'] = _book_name
            book['url'] = _book_dow_fullurl
            book['down_dir_path'] =  book_dir
            data['books'].append(book);
    
       
def doWork():
    while True:
        _book = q.get()
        _status = downloadEbooks(_book)
        #doSomethingWithResult(_status, _book['url'])
        
        q.task_done()
        print('Downloaded End , TOTAL BOOKS COUNTS: {0}'.format(books_downloaded_count))
        sys.exit(1)

def downloadEbooks(_book):
    try:
        global books_downloaded_count
        _book_abs_path = os.path.join(_book['down_dir_path'], _book['name']+'.pdf')
        _book_grade = _book['down_dir_path'].split('\\')[-2]
        _book_subject = _book['down_dir_path'].split('\\')[-1]
        _book_name = _book['name']
        print('{0}/{1}/{2} Downloading....'.format(_book_name, _book_grade , _book_subject))
        resp = requests.get(_book['url'])
        if resp.status_code == 200:
            
            with open(_book_abs_path, 'wb') as f:
                ##for chunk in res.iter_content(chunk_size=128):
                ##    f.write(chunk)
                ## return resp.status
                try: 
                    f.write(resp.content)
                    books_downloaded_count+=1
                    print('{0}/{1}/{2} Downloaded Successfully!'.format(_book_name, _book_grade , _book_subject))
                except err:
                    print(err)
                    sys.exit(1)
            resp.close()
    except:
        return "error: "


def doSomethingWithResult(status, url):
    print(status, url)
       
        

           

pep_dir = r'D:\成都七中网课_202002\人教版教材'

if res.status_code == 200:
    soup = BeautifulSoup(res.text, 'lxml')
    res.close()
    list_jcdzs = soup.find_all('div', class_='list_sjzl_jcdzs2020')
    for  item in list_jcdzs:
        _container = {}
        ## parent dir eg.义务教育教科书（小学）
        _container['dir'] = item.find('h5').string
        # 1. create parent dir
        Path(os.path.join(pep_dir,_container['dir'])).mkdir(parents=True, exist_ok=True)
        #print('{0} Dir Created'.format(_container['dir']))
        _container['subject'] = []
        list_grade_links = item.select('ul.clearfix.js_cp > li.fl > a')
        for link in list_grade_links:
            subject = {}
            subject['subdir'] = link.get_text()
            #2 create subject dir
            Path(os.path.join(pep_dir,_container['dir'], subject['subdir'] )).mkdir(parents=True, exist_ok=True)
            #print('{0} Dir Created'.format(subject['subdir']))
            ## request detail url     
            subject['link'] = link['href']
            # book's dir path to download in 
            _book_dir = os.path.join(pep_dir, _container['dir'], subject['subdir'])
           
            ''' 
            getEbooksRequest
                @param: _url
                @param: book_dir
            '''
            #print(_book_dir)
            #3 request to get sub dir books 
            getEbooksRequest(link['href'], _book_dir, _container['dir'], subject['subdir'])

     # 4 write data['books'] to json file
        
    with open('./data.json','w') as outfile:
        json.dump(data,outfile,ensure_ascii=False,indent=4)
    
    print('###Total BOOKS: {0}'.format(books_counts))
    # 5  Queue 
    concurrent = 2000
    q = queue.Queue(concurrent * 2)
    for i in range(concurrent):
        
        t = Thread(target=doWork)
        t.daemon = True
        t.start()
    
    try:
        with open('./data.json','r') as outfile:
            _data = json.load(outfile)
            book_data = _data['books']
            for book in book_data:
                q.put(book)
            q.join()
    except KeyboardInterrupt:
        sys.exit(1)



