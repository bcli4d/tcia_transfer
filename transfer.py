import pdb
import argparse
import os
from google.cloud import storage
from tciaclient import TCIAClient
import urllib2, urllib,sys
####################################  Function to print server response #######
def printServerResponse(response):
    if response.getcode() == 200:
        print "Server Returned:\n"
        print response.read()
        print "\n"
    else:
        print "Error: " + str(response.getcode())

# Create Clients for Two Different Resources  ####
def createClients(keyFile):
    with open(keyFile) as f:
        apiKey = f.readline().strip()
    tcia_client = TCIAClient(apiKey,baseUrl="https://services.cancerimagingarchive.net/services/v3",resource = "TCIA")
    #tcia_client2 = TCIAClient(apiKey,baseUrl="https://services.cancerimagingarchive.net/services/v3",resource="SharedList")

    return tcia_client
    
# Get all studies of some collection
def getStudies(tcia_client,args):
    studies = ""
    try:
        response = tcia_client.get_patient_study(collection = args.collection, patientId = None,studyInstanceUid = None, outputFormat = "csv")
        studies = response.read().splitlines()[1:];

        if args.verbosity>1 :
            print "Studies: ", studies
            print '\n'
            
    except urllib2.HTTPError, err:
        print "Errror executing program:\nError Code: ", str(err.code), "\nMessage:", err.read()

    return studies

# Get series of a study
def getSeries(tcia_client,studyInstanceUid,args):
    try:
        response = tcia_client.get_series(collection = "REMBRANDT",modality = None,studyInstanceUid = studyInstanceUid, outputFormat = "csv")
        series = response.read().splitlines()[1:];

        if args.verbosity>1 :
            print 'Study, series: ', studyInstanceUid, series
            print '\n'

    except urllib2.HTTPError, err:
        print "Errror executing program:\nError Code: ", str(err.code), "\nMessage:", err.read()

    return series

# Upload zip file to GCS
#def uploadToGcs(args, patientName, seriesInstanceUid):
def upload_blob(storage_client, bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print('File {} uploaded to {}.'.format(
        source_file_name,
        destination_blob_name))

def parseargs():
    parser = argparse.ArgumentParser(description='Transfer TCIA images to GCS')
    parser.add_argument ( "-v", "--verbosity", action="count",default=0,help="increase output verbosity" )
    parser.add_argument ( "-k", "--key", type=str, help="api-key file name", default='api-key.txt')
    parser.add_argument ( "-b", "--bucket", type=str, help="Name of bucket to upload to", default='isb-tcia-open')
    parser.add_argument ( "-c", "--collection", type=str, help="TCIA collection from which to download", default='REMBRANDT')
    return(parser.parse_args())

if __name__ == '__main__':
    args=parseargs()
    print(args)

    tcia_client = createClients(args.key)               
    storage_client = storage.Client()

    studies = getStudies(tcia_client, args)
    for study in studies:
        studyInstanceUid = study.split(',')[4][1:-1]
        patientName = study.split(',')[1][1:-1]
        series = getSeries(tcia_client, studyInstanceUid, args)
        for s in series:
            seriesInstanceUid = s.split(',')[0][1:-1]
            if args.verbosity > 1:
                print 'Downloading series ', s
            zipFileName = seriesInstanceUid+'.zip'
            tcia_client.get_image(seriesInstanceUid , downloadPath  ='./', zipFileName = zipFileName);
            upload_blob(storage_client, args.bucket, zipFileName, 'images/'+args.collection+'/'+patientName+'/'+zipFileName)
            os.remove(zipFileName)
