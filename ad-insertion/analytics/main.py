#!/usr/bin/python3

from messaging import Consumer
from runva import RunVA
import ast
from zkstate import ZKState
import merged_segment as merge
import datetime
import json
import socket
import time
import os
import re

video_analytics_topic = "seg_analytics_sched"
machine_prefix=os.environ.get("VA_PRE")
if machine_prefix == None:
    machine_prefix="VA-"
va=RunVA()

def process_stream(zk, streamstring):
    streamjson = ast.literal_eval(streamstring)
    pipeline1 = streamjson["pipeline"]+"/1"
    stream = streamjson['source']['uri']
    print("VA feeder: stream: "+stream, flush=True)
    init_stream = None
    zk_path = None
    if 'uri-init' in streamjson['source']:
        init_stream = streamjson['source']['uri-init']
        print("VA feeder: init_stream: "+init_stream, flush=True)
        zk_path = stream+"/"+pipeline1

    m1 = re.search("(.*)/.*_([0-9]+.ts)$", stream)
    if m1:
        segment = stream.split('/')[-1].split('_')[-1]
        zk_path = m1.group(1)+"/"+segment+"/"+pipeline1

    print("VA feeder: zk_path "+zk_path, flush=True)
    zk.set_path(zk_path)
    if zk.processed():
        print("VA feeder: " + stream + " already complete", flush=True)
        return
    if zk.process_start():
        merged_segment = None
        if init_stream:
            merged_segment = merge.create_merged_segment(init_stream, stream)
            if merged_segment:
                stream = "file://" + merged_segment
                print("VA feeder: video-analytics merged segment: " +
                      stream, flush=True)
        
        fps=va.loop({
            "source": {
                "uri": stream,
                "type":"uri"
            },
            "destination": {
                "type": "kafka",
                "host": socket.gethostbyname("kafka-service")+":9092",
                "topic": "seg_analytics_data"
            },
            "tags": streamjson["tags"],
            "parameters": streamjson["parameters"],
        }, streamjson["pipeline"])
        if fps<0:
            zk.process_abort()
        else:
            zk.process_end()
            
        if merged_segment:
            merge.delete_merged_segment(merged_segment)

if __name__ == "__main__":
    c = Consumer("analytics")
    zk = ZKState()
    while True:
        try:
            print("VA feeder: listening to messages", flush=True)
            for msg in c.messages(video_analytics_topic):
                print("VA feeder: recieved message: " + str(msg), flush=True)
                try:
                    process_stream(zk, msg)
                except Exception as e:
                    print("VA feeder: "+str(e), flush=True)
        except Exception as e:
            print("VA feeder: error in main" + str(e), flush=True)
            time.sleep(1)
    c.close()
    zk.close()
