import boto3
import sys
import random
import string
import requests
import webbrowser
import json
import subprocess
import paramiko

#intialize EC2 and s3 resource
ec2 = boto3.resource("ec2")
s3 = boto3.resource("s3")
s3client = boto3.client("s3")
public_ip = None

#Create new EC2 instance with specified configuration
new_instances = ec2.create_instances ( ImageId = "ami-00c6177f250e07ec1",
                                       MinCount = 1,
                                       MaxCount = 1,
                                       InstanceType = "t2.nano",
                                       KeyName="Keyster",
                                       SecurityGroupIds=["SecurityGroupsted"],
                                       UserData="""#!/bin/bash
                                                    yum install httpd -y
                                                    systemctl enable httpd
                                                    systemctl start httpd
                                                    INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
                                                    echo Instance ID: $INSTANCE_ID > /var/www/html/index.html
                                                    AVAILABILITY_ZONE=$(curl http://169.254.169.254/latest/meta-data/placement/availability-zone)
                                                    echo Availability zone: $AVAILABILITY_ZONE >> /var/www/html/index.html
""")
print("Created new instance")
print(new_instances[0].id)

new_instances[0].wait_until_running()


while public_ip is None:
    new_instances[0].reload()  # Reload the instance information
    public_ip = new_instances[0].public_ip_address
    if public_ip is None:
        print("Public IP has not been assigned yet. Trying again in 10 seconds")
        time.sleep(10)
    else:
        print("Public IP address:", public_ip)

#generate random bucket name
characters = string.ascii_lowercase + string.digits
bucket_name = ''.join(random.choice(characters) for i in range(6))
bucket_name = bucket_name + "-dlarsen"
print("Random bucket name is:", bucket_name)


#Create S3 bucket with the generated name
try:
    response = s3.create_bucket(Bucket=bucket_name)
    print (response)
except Exception as error:
    print (error)



s3client.delete_public_access_block(Bucket=bucket_name)
print("deleting public access block")

#Setting up bucket policy so public can get read access
bucket_policy = {
    "Version": "2012-10-17",
    "Statement": [
{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": ["s3:GetObject"],
    "Resource": f"arn:aws:s3:::{bucket_name}/*"
}
]
}

#applying the bucket policy to the s3 bucket
s3.Bucket(bucket_name).Policy().put(Policy=json.dumps(bucket_policy))
print("setting up public policy and applying it")
#Downloading image from website to pc
picFromUrl = "http://devops.witdemo.net/logo.jpg"
with open("logo.jpg", "wb") as logo:
    img = requests.get(picFromUrl).content
    logo.write(img)
    print("Image download completed")

#Upload of website and picture to the s3 bucket 
s3.Object(bucket_name, "index.html").put(Body=open("index.html", 'rb'), Key='index.html', ContentType='text/html')
s3.Object(bucket_name, "logo.jpg").put(Body=open("logo.jpg", 'rb'), Key='logo.jpg', ContentType='img/jpeg')

#configure S3 bucket to be a website
website_configuration = {
    'ErrorDocument': {'Key': 'error.html'},
    'IndexDocument': {'Suffix': 'index.html'},
}
bucket_website = s3.BucketWebsite(bucket_name)
bucket_website.put(WebsiteConfiguration=website_configuration)

bucket_website.put(WebsiteConfiguration=website_configuration)


#Open browser tabs for the s3 bucket
webbrowser.open_new_tab(f"http://{bucket_name}.s3.amazonaws.com/index.html")
webbrowser.open_new_tab(f"http://{public_ip}")
print("Websites opened")

#creating text file with website names
websites = open("dlarsen-websites.txt", "w+")
websites.write(bucket_name +  public_ip)
websites.close()
print("created text file with website urls")

key_path = "/home/thisted/Keyster.pem"  # Replace with the path to your private key file

# copying monitoring to ec2 instance
scp_cmd = f"scp -i {key_path} monitoring.sh ec2-user@{public_ip}:."
scp_result = subprocess.run(scp_cmd, shell=True)
print("SCP Return Code:", scp_result.returncode)

# Then running the monitoring script
ssh_cmd = f"ssh -o StrictHostKeyChecking=no -i {key_path} ec2-user@{public_ip} 'chmod 700 monitoring.sh'"
ssh_result = subprocess.run(ssh_cmd, shell=True)
print("SSH Return Code:", ssh_result.returncode)