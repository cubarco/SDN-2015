#!/usr/bin/env python
# coding=utf8


from apscheduler.schedulers.background import BackgroundScheduler


class SchedulerWrapper(object):
    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self.jobs = []

    def start(self):
        self._scheduler.start()

    def add_job(self, func, id, args=None, kwargs=None, interval=1):
        ''' Interval: seconds '''
        job = self._scheduler.add_job(func, 'interval', args=args, kwargs=None,
                                      seconds=interval, id=id)
        self.jobs.append(job)

    def remove_job(self, id):
        for job in self.jobs:
            if job.id == id:
                job.remove()

    def get_jobs(self):
        return self.jobs
