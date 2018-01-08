import boto3
import os
import paramiko
import logging
import inspect

LOG_STATUS = True
SSH_KEY_S3_BUCKET = os.environ['SshKeyS3Bucket']
SSH_KEY_S3_KEY = os.environ['SshKeyS3Key']
EC2_USER = os.environ['Ec2User']


def log(msg):
    if LOG_STATUS:
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        referrer = calframe[1][3]
        print ("%s: %s" % (referrer, msg))


def get_key():
    if not os.path.isfile("/tmp/keyname.pem"):
        s3_client = boto3.client('s3')
        s3_client.download_file(
            SSH_KEY_S3_BUCKET,
            SSH_KEY_S3_KEY,
            '/tmp/keyname.pem'
        )
        log('ssh_key downloaded')
    return paramiko.RSAKey.from_private_key_file("/tmp/keyname.pem")


def notify_ec2_instance(instance, cmd):
    log('Notifying instance: ' + instance['InstanceId'])
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=instance['PrivateIpAddress'], username=EC2_USER, pkey=get_key())
        # Execute a command(cmd) after connecting/ssh to an instance
        (stdin, stdout, stderr) = client.exec_command(cmd)
        for line in stdout.readlines():
            log(line)
        # close the client connection once the job is done
        client.close()
    except Exception as e:
        logging.exception(e.message)
    log('Notified')


def get_instances(filters):
    ec2 = boto3.client('ec2')
    reservations = ec2.describe_instances(Filters=filters)
    log("Found %d instance(s)" % len(reservations['Reservations']))
    return reservations['Reservations']


def get_running_instances_by_name(names):
    log('GetRunning instances by name "' + ', '.join(str(e) for e in names) + '"')
    filters = [
        {
            'Name': 'tag:Name',
            'Values': names
        },
        {
            'Name': 'instance-state-name',
            'Values': ['running']
        },
    ]
    return get_instances(filters=filters)


def notify_instances(names, cmd, once):
    log('Notify instances...')
    reservations = get_running_instances_by_name(names)
    for reservation in reservations:
        notify_ec2_instance(reservation['Instances'][0], cmd)
        if once:
            break
    log('All instances notified.')


def lambda_handler(event, _context):
    try:
        log('Start')
        notify_instances(event['InstanceNames'], event['cmd'], bool(event['once']))
        log('Done sucessfully.')
    except Exception as e:
        logging.exception("Failed: %s" % e.message)
