import csv
import datetime
import json
import os
import time
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.adreportrun import AdReportRun
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError


class CSVGenerator:
    def __init__(self):
        self.base_fields = ['day', 'campaign_name', 'campaign_id', 'adset_name', 'adset_id', 'ad_name',
                            'ad_id', 'account_currency', 'spend', 'impressions', 'reach', 'frequency',
                            'link_clicks', 'qualified_traffic', 'adds_to_wishlist', 'purchase_post_paid',
                            '3_second_video_plays', 'video_p25_watched_actions', 'video_p50_watched_actions',
                            'video_p75_watched_actions', 'video_p100_watched_actions', 'attribution_setting',
                            'description', 'headline', 'website_url',
                            'call_to_action_type', 'image_name', 'video_name', 'url_parameters', 'objective']

    def convert_rows(self, rows, csv_fields):
        row_keys_to_delete = []
        for i in range(len(rows)):
            for row_key in list(rows[i]):
                if row_key == 'unique_inline_link_clicks':
                    rows[i]['link_clicks'] = rows[i][row_key]
                elif row_key == 'actions':
                    for action in rows[i][row_key]:
                        if action['action_type'] == 'offsite_conversion.fb_pixel_add_to_wishlist':
                            rows[i]['adds_to_wishlist'] = action['value']
                        elif action['action_type'] == 'video_view':
                            rows[i]['3_second_video_plays'] = action['value']
                        elif action['action_type'] == 'offsite_conversion.fb_pixel_custom':
                            rows[i]['qualified_traffic'] = action['value']
                elif row_key == 'date_start':
                    rows[i]['day'] = rows[i][row_key]
                elif row_key in ['video_p25_watched_actions', 'video_p50_watched_actions',
                            'video_p75_watched_actions', 'video_p100_watched_actions']:
                    try:
                        rows[i][row_key] = rows[i][row_key][0]['value']
                    except TypeError:
                        pass
        for i in range(len(rows)):
            for row_key in rows[i].keys():
                if row_key not in csv_fields:
                    row_keys_to_delete.append((i, row_key))
        for row_key in row_keys_to_delete:
            del rows[row_key[0]][row_key[1]]
        for i in range(len(rows)):
            for csv_field in csv_fields:
                if csv_field not in rows[i].keys():
                    rows[i][csv_field] = None

        return rows

    def generate_report(self, rows, report_breakdowns):
        csv_fields = self.base_fields
        for breakdown in report_breakdowns:
            csv_fields.append(breakdown)
        rows = self.convert_rows(rows, csv_fields)
        if 'region' in report_breakdowns:
            self.create_csv(f'region_{datetime.datetime.today().strftime("%Y-%m-%d")}.csv', csv_fields, rows)
        elif 'age' in report_breakdowns:
            self.create_csv(f'age-{datetime.datetime.today().strftime("%Y-%m-%d")}.csv', csv_fields, rows)
        elif 'impression_device':
            self.create_csv(f'impression-{datetime.datetime.today().strftime("%Y-%m-%d")}.csv', csv_fields, rows)

    @staticmethod
    def create_csv(output_filename, fieldnames, output_rows):
        with open(os.path.join(output_filename), 'w') as csv_file:
            output_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            output_writer.writeheader()
            for row in output_rows:
                output_writer.writerow(row)


class FacebookReporter:
    def __init__(self):
        app_id = '769583813938024'
        app_secret = '0d785a6bb23bc248a827fed820fe4ea0'
        access_token = 'EAAK77rHay2gBANEqlTi1DEbX7oDnyGbu9d3crWlPTHDHeeRL32WtPAPW0yn3cafTw98VXaTpwBZCubl20jRijqZBZCANU9RtMKdJWoYkXRZChW0IFEvJmBw7YrybTFsrnoKH3JvYZBGZAeuRYNMs4Agb2bsO1aeCGFVk3YlqjehRDAKqkXPEuZA'
        self.facebook_api = FacebookAdsApi.init(app_id, app_secret, access_token)
        self.ad_account = AdAccount('act_881123992711859')
        self.fields = ['video_play_actions', 'video_p25_watched_actions', 'video_p50_watched_actions',
                       'video_p75_watched_actions', 'video_p100_watched_actions',
                       'attribution_setting', 'objective', 'reach', 'impressions', 'frequency', 'account_currency',
                       'campaign_id', 'campaign_name', 'adset_name', 'adset_id', 'ad_name', 'ad_id',
                       'ad_impression_actions', 'spend', 'unique_inline_link_clicks', 'actions'
                       ]

        self.params = {

            'level': 'ad',
            'date_preset': 'last_30d',
            'time_increment': 1,
            'use_unified_attribution_setting': True,
            'default_summary': True,

        }
        self.current_ads = []

    def get_ad_data_or_sleep(self, ad):
        while True:
            ad_data = {'ad_id': ad}

            try:

                ad = Ad(ad)

                creative = AdCreative(ad.api_get(fields=[Ad.Field.creative])['creative']['id'])
                fields = [AdCreative.Field.call_to_action_type, AdCreative.Field.object_story_spec]

                creative.api_get(fields=fields)
                creative = dict(creative)
                try:
                    call_to_action = creative['object_story_spec']['video_data']['call_to_action']
                    try:
                        print(creative['object_story_spec']['photo_data'])
                    except KeyError:
                        pass

                    ad_data['website_url'] = call_to_action['value']['link']

                    ad_data['call_to_action_type'] = call_to_action['type']
                    ad_data['headline'] = creative['object_story_spec']['video_data']['title']
                    ad_data['description'] = creative['object_story_spec']['video_data']['message']

                    video = AdVideo(creative['object_story_spec']['video_data']['video_id'])
                    ad_data['video_name'] = video.api_get(fields=[AdVideo.Field.title])['title']
                except KeyError:
                    pass
                self.current_ads.append(ad_data)
            except FacebookRequestError as e:
                print(type(e.api_error_code()))
                if e.api_error_code() == 803:
                    break
                print('Sleeping right now for ads')

                time.sleep(600)
            else:
                break

        return ad_data

    def get_ads_or_sleep(self):
        ads_list = []
        while True:
            try:
                account_ads = self.ad_account.get_ads(fields=[Ad.Field.id])
                for ad in account_ads:
                    ads_list.append(dict(ad))
            except FacebookRequestError:
                time.sleep(1200)
            else:
                break
        return ads_list

    def generate_ad_data(self):
        ads = []
        ads_data = self.get_ads_or_sleep()
        for ad in ads_data:
            ad_data = self.get_ad_data_or_sleep(ad)

            ads.append(ad_data)
        return ads

    def get_insights_or_sleep(self, campaign):
        while True:
            try:
                insights = campaign.get_insights(fields=self.fields, params=self.params, is_async=True)
                insights.api_get()
                while insights[AdReportRun.Field.async_status] != 'Job Completed' or insights[AdReportRun.Field.async_percent_completion] < 100:
                    time.sleep(1)
                    insights.api_get()
                    print(insights[AdReportRun.Field.async_percent_completion])
                time.sleep(1)
                insights = insights.get_result()
            except FacebookRequestError:
                print('Sleeping right now for insights')
                time.sleep(600)
            else:
                break
        return insights

    def get_campaigns_or_sleep(self):
        while True:
            try:
                campaigns = self.ad_account.get_campaigns()
            except FacebookRequestError:
                print('Sleeping right now for campaigns')
                time.sleep(30)
            else:
                break
        return campaigns

    def generate_report(self, breakdowns):
        rows = []
        campaigns = []
        for campaign in self.get_campaigns_or_sleep():
            campaigns.append(campaign)
        for i in range(len(campaigns)):

            self.params['breakdowns'] = breakdowns
            insights = self.get_insights_or_sleep(campaigns[i])
            for y in range(len(insights)):
                insight = dict(insights[i])
                print(insight)
                flag = False
                for ad in self.current_ads:
                    if ad['ad_id'] == insight['ad_id']:
                        insight.update(ad)
                        flag = True
                        break
                if not flag:
                    insight.update(self.get_ad_data_or_sleep(insight['ad_id']))
                rows.append(insight)
                print(f'Pulling dats for campaign, {i}/{len(campaigns)}, {y}/{len(insights)}')
                try:
                    with open('test.json', 'w') as f:
                        f.write(json.dumps(rows))
                except:
                    with open('test2.txt', 'w') as f:
                        f.write(str(insight))
                    rows.remove(insight)

            CSVGenerator().generate_report(rows, breakdowns)


if __name__ == "__main__":
    #FacebookReporter().generate_report(['region'])
    FacebookReporter().generate_report(['age', 'gender'])
    FacebookReporter().generate_report(['impression_device', 'device_platform', 'platform_position',
                                        'publisher_platform'])
