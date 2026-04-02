import os,time,json;from gdrive_api import GoogleDriveAPI;from meta_api import MetaAPI
def main():
   drive=GoogleDriveAPI();meta=MetaAPI();queue=[]
   try:
       with open("schedule_queue.json","r") as f:queue=json.load(f)
          except:pass
             now=time.time()
 for i in queue:
     if i.get('schedule_time',0)<=now:
          for a in i.get('accounts',[]):meta.post_reel(a,i.get('gdrive_id'),i.get('caption'))
 main()
