import boto3,sys,time
ssm=boto3.client('ssm'); iid='i-01eeae171d57f9615'
cmd=sys.argv[1]
r=ssm.send_command(InstanceIds=[iid],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]})
cid=r['Command']['CommandId']
while True:
    time.sleep(2)
    try: o=ssm.get_command_invocation(CommandId=cid,InstanceId=iid)
    except ssm.exceptions.InvocationDoesNotExist: continue
    if o['Status'] not in ('Pending','InProgress','Delayed'): break
print(o['Status']); print(o['StandardOutputContent']); print(o['StandardErrorContent'],file=sys.stderr)
