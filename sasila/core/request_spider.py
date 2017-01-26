#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

import gevent
import gevent.monkey
from sasila.scheduler.url_scheduler import PriorityQueue

from sasila.downloader.spider_request import Request
from sasila.downloader.requests_downloader import RequestsDownLoader
from sasila.util import logger

gevent.monkey.patch_all()
reload(sys)
sys.setdefaultencoding('utf-8')


class RequestSpider(object):
    def __init__(self, processor, downloader=None, scheduler=None):
        self._processor = processor
        self._spider_status = 0
        self._pipelines = []
        self._spider_name = processor.spider_name
        self._spider_id = processor.spider_id

        if not downloader:
            self._downloader = RequestsDownLoader()

        if not scheduler:
            self._scheduler = PriorityQueue(self._spider_id)

    def create(self, processor):
        self._processor = processor
        return self

    def set_scheduler(self, scheduler):
        self._scheduler = scheduler
        return self

    def set_downloader(self, downloader):
        self._downloader = downloader
        return self

    def set_pipeline(self, pipeline):
        self._pipelines.append(pipeline)
        return self

    def get_status(self):
        return self._spider_status

    def init_component(self):
        pass

    def start(self):
        if len(self._processor.start_requests) > 0:
            for start_request in self._processor.start_requests:
                self._scheduler.push(start_request)
                logger.info("start request:" + str(start_request))
        for batch in self._batch_requests():
            if len(batch) > 0:
                gevent.joinall([gevent.spawn(self._crawl, r) for r in batch])

    def _batch_requests(self):
        batch = []
        count = 0
        while True:
            count += 1
            if len(batch) > 99 or count > 99:
                yield batch
                batch = []
                count = 0
            temp_request = self._scheduler.pop()
            if temp_request:
                batch.append(temp_request)

    def _crawl(self, request):
        if not request.callback:
            request.callback = self._processor.process
        response = self._downloader.download(request)
        for item in request.callback(response):
            if isinstance(item, Request):
                logger.info("push request to queue..." + str(item))
                self._scheduler.push(item)
            else:
                for pipeline in self._pipelines:
                    pipeline.process_item(item)
