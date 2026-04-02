import os,time,json;from gdrive_api import GoogleDriveAPI;from meta_api import MetaAPI;
def main():
             drive=GoogleDriveAPI();meta=MetaAPI();queue=[];
             try:
                           with open("schedule_queue.json","r") as f:queue=json.load(f)
                                        except:pass
                                                     now=time.time()
 for item in queue:
               if item.get('schedule_time',0)<=now:
                              for acc in item.get('accounts',[]):meta.post_reel(acc,item.get('gdrive_id'),item.get('caption'))
                                          main()
