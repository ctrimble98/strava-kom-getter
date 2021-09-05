#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re

VERSION = '0.1.0'

class SegmentEffort:

    def __init__(self, name, activity_id=None):

        self.name = name
        self.activity_id = activity_id

    def __str__(self):
        return("Name:{} - ActivityId:{} - Time(s):{}".format(self.name,self.activity_id,self.time))

    def set_time(self, time_string):
        '''
        Sets a time attribute in seconds

        Sample inputs:
        "1:04"
        "58<abbr class='unit' title='second'>s</abbr>"
        '''

        # TODO Verify if required for hours
        seconds_matcher = re.compile(r"(?<=title='second'>).*(?=</abbr>)")
        if re.search(seconds_matcher, time_string):
            self.time = time_string.split("<")[0]
            return

        #Catch errors in case variant outside of seconds and a minutes timestamp exists
        try:
            split_time = time_string.split(":")
            self.time = int(split_time[0])*60 + int(split_time[1])
        except:
            print("ERROR with extracting time from \"{}\"".format(time_string))
            self.time = None


class SegmentScraper:

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent
    USER_AGENT = "kom-getter/%s" % VERSION
    HEADERS = {'User-Agent': USER_AGENT}

    BASE_URL = "https://www.strava.com"
    URL_SEGMENTS = "%s/segments" % BASE_URL

    def __init__(self):
        self.session = requests.Session()

    def get_page(self, url):

        response = self.session.get(url, headers=SegmentScraper.HEADERS)
        response.raise_for_status()

        response_text = response.content.decode("utf-8")
        return response_text

    def get_leaderboard_html(self, html_text):
        '''Func to get overall leaderboard html from strava /segments/<id> page'''

        leaderboard_matcher = re.compile(r"(?<=<h2 class='text-title1'>Overall Leaderboard</h2>.{1}<table class='table table-striped table-leaderboard'>)(.*?)(?=</table>)", re.DOTALL)
        leaderboards = re.findall(leaderboard_matcher, html_text)

        matcher = re.compile(r"(?<=<tr>)(.*?)(?=</tr>)", re.DOTALL)
        overall_leaderboard = re.findall(matcher, leaderboards[0])

        # Remove headings from table
        overall_leaderboard=overall_leaderboard[1:]

        return overall_leaderboard


    def get_segment_effort(self, raw_effort):
        '''Func to get a SegmentEffort object from the raw html of an effort'''

        field_matcher = re.compile(r"(?<=<td>)(.*?)(?=</td>)")
        effort_fields = re.findall(field_matcher, raw_effort)

        if len(effort_fields) < 2:
            print("ERROR with athlete fields: {}".format(effort_fields))
            print("Skipping athlete")
            return None
        
        # Pull name out of the entry for the athlete
        name_string = effort_fields[1]

        activity_matcher = re.compile(r"(?<=<a href=\"/activities/)(.*?)(?=\">)")
        time_matcher_string = (r"(?<=<a href=\"/activities/{}\">)(.*?)(?=</a>)")
        for field in effort_fields:

            # Activity must be matched first in order as regex look back cant deal with variable lengths
            #    so activity id must be extracted to construct regex string
            activity = re.search(activity_matcher, field)

            if not activity:
                continue

            activity = activity.group(0)
            time_matcher = re.compile(time_matcher_string.format(activity))
            time_string = re.search(time_matcher, field).group(0)

            if not time_string:
                continue

            effort = SegmentEffort(name_string, activity)
            effort.set_time(time_string)

            return effort

		
    def extract_segment_time(self, segment_id):
        '''
        Get the segement leaderboard for a segment and extract it into a list of SegmentEffort objects
        '''

        segment_url = "{}/{}".format(SegmentScraper.URL_SEGMENTS, segment_id)

        response_text = self.get_page(segment_url)

        leaderboard = self.get_leaderboard_html(response_text)

        efforts = []
        for raw_effort in leaderboard:

            effort = self.get_segment_effort(raw_effort)
            efforts.append(effort)

        return efforts

def main():
    import sys

    if len(sys.argv) < 2:
        print(sys.stderr, "Usage: ./scraper.py \"segment_id\"")
        sys.exit(1)

    segment_id = sys.argv[1]
        
    scraper = SegmentScraper()
    efforts = scraper.extract_segment_time(segment_id)

    if efforts:
        kom = efforts[0]
        print("KOM for segment: {} is {} with a time of {} seconds".format(segment_id, kom.name, kom.time))
        print()
        print("Top 10:")
        print("\n".join([str(effort) for effort in efforts]))

if __name__ == '__main__':
    main()