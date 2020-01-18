import falcon
import traceback
import yaml
import logging
import requests
import sys
import base64
from falcon.http_status import HTTPStatus
import psycopg2.extras
from datetime import datetime
from wsgiref import simple_server
from dateutil.parser import parse
from app.util.db_connection import DbConnection
from app.queries import QUERY_CHECK_CONNECTION, QUERY_SELECT_ALL, QUERY_INSERT_CHART

class AppService:
    def __init__(self):
        print('Initializing App Service...')
        self.dbconnection = DbConnection('db_credentials.yaml')

    def on_get(self, req, resp):
        print('HTTP GET: /charts')
        cursor = self.dbconnection.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(QUERY_SELECT_ALL)
        response = []
        for record in cursor:
            response.append(
                {
                    'chart_id': record[0],
                    'note': record[1],
                    'symbol': record[2],
                    'image': record[3]
                }
            )

        resp.status = falcon.HTTP_200
        resp.media = { 'charts': response}
        cursor.close()

    # todo: add optional trainingId parameter
    def on_post(self, req, resp):
        con = self.dbconnection.connection
        try:
            print('HTTP POST: /charts')
            cursor = con.cursor()
            base64_bytes = base64.b64decode(req.media['image'])
            cursor.execute(QUERY_INSERT_CHART, (req.media['note'], req.media['symbol'], base64_bytes))
            con.commit()

            resp.status = falcon.HTTP_200
            resp.media = {
                "message": "hi"
            }

        except psycopg2.DatabaseError as e:
            if con:
                con.rollback()
            print ('Error %s' % e ) 
            sys.exit(1)
        finally: 
            if cursor:
                cursor.close()

def start_service():
    service = AppService()

    app = falcon.API(middleware=[HandleCORS()])
    app.add_route('/charts', service)
    return app

class HandleCORS(object):
    def process_request(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', '*')
        resp.set_header('Access-Control-Allow-Headers', '*')
        resp.set_header('Access-Control-Max-Age', 1728000)  # 20 days
        if req.method == 'OPTIONS':
            raise HTTPStatus(falcon.HTTP_200, body='\n')

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')