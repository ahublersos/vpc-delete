"""

Remove those pesky AWS default VPCs.

Python Version: 3.7.0
Boto3 Version: 1.7.50

"""

import sys
import boto3
from botocore.exceptions import ClientError
dryrun = True

def delete_igw(ec2, vpc_id):
  """
  Detach and delete the internet gateway
  """

  args = {
    'Filters' : [
      {
        'Name' : 'attachment.vpc-id',
        'Values' : [ vpc_id ]
      }
    ]
  }

  try:
    igw = ec2.describe_internet_gateways(**args)['InternetGateways']
  except ClientError as e:
    print(e.response['Error']['Message'])

  if igw:
    igw_id = igw[0]['InternetGatewayId']

    try:
      if not dryrun:
        print("  Detaching " + str(igw_id))
        result = ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
      else:
        print("(Dry-run)  Detaching " + str(igw_id))
    except ClientError as e:
      print(e.response['Error']['Message'])

    try:
      if not dryrun:
        print("  Deleting " + str(igw_id))
        result = ec2.delete_internet_gateway(InternetGatewayId=igw_id)
      else:
        print("(Dry-run)  Deleting " + str(igw_id))
    except ClientError as e:
      print(e.response['Error']['Message'])

  return


def delete_subs(ec2, args):
  """
  Delete the subnets
  """

  try:
    subs = ec2.describe_subnets(**args)['Subnets']
  except ClientError as e:
    print(e.response['Error']['Message'])

  if subs:
    for sub in subs:
      sub_id = sub['SubnetId']

      try:
        if not dryrun:
          print("  Deleting " + str(sub_id))
          result = ec2.delete_subnet(SubnetId=sub_id)
        else:
          print("(Dry-run)  Deleting " + str(sub_id))
      except ClientError as e:
        print(e.response['Error']['Message'])

  return


def delete_rtbs(ec2, args):
  """
  Delete the route tables
  """

  try:
    rtbs = ec2.describe_route_tables(**args)['RouteTables']
  except ClientError as e:
    print(e.response['Error']['Message'])

  if rtbs:
    for rtb in rtbs:
      main = 'false'
      for assoc in rtb['Associations']:
        main = assoc['Main']
      if main == True:
        continue
      rtb_id = rtb['RouteTableId']
        
      try:
        if not dryrun:
          print("  Deleting " + str(rtb_id))
          result = ec2.delete_route_table(RouteTableId=rtb_id)
        else:
          print("(Dry-run)  Deleting " + str(rtb_id))
      except ClientError as e:
        print(e.response['Error']['Message'])

  return


def delete_acls(ec2, args):
  """
  Delete the network access lists (NACLs)
  """

  try:
    acls = ec2.describe_network_acls(**args)['NetworkAcls']
  except ClientError as e:
    print(e.response['Error']['Message'])

  if acls:
    for acl in acls:
      default = acl['IsDefault']
      if default == True:
        continue
      acl_id = acl['NetworkAclId']

      try:
        if not dryrun:
          print("  Deleting " + str(acl_id))
          result = ec2.delete_network_acl(NetworkAclId=acl_id)
        else:
          print("(Dry-run)  Deleting " + str(acl_id))
      except ClientError as e:
        print(e.response['Error']['Message'])

  return


def delete_sgps(ec2, args):
  """
  Delete any security groups
  """

  try:
    sgps = ec2.describe_security_groups(**args)['SecurityGroups']
  except ClientError as e:
    print(e.response['Error']['Message'])

  if sgps:
    for sgp in sgps:
      default = sgp['GroupName']
      if default == 'default':
        continue
      sg_id = sgp['GroupId']

      try:
        if not dryrun:
          print("  Deleting " + str(sg_id))
          result = ec2.delete_security_group(GroupId=sg_id)
        else:
          print("(Dry-run)  Deleting " + str(sg_id))
      except ClientError as e:
        print(e.response['Error']['Message'])

  return


def delete_vpc(ec2, vpc_id, region):
  """
  Delete the VPC
  """

  try:
    if not dryrun:
      print("  Deleting " + str(vpc_id))
      result = ec2.delete_vpc(VpcId=vpc_id)
    else:
      print("(Dry-run)  Deleting " + str(vpc_id))
  except ClientError as e:
    print(e.response['Error']['Message'])

  else:
    if not dryrun:
      print('VPC {} has been deleted from the {} region.'.format(vpc_id, region))
    else:
      print('(Dry-run) VPC {} has been deleted from the {} region.'.format(vpc_id, region))

  return


def get_regions(ec2):
  """
  Return all AWS regions
  """

  regions = []

  try:
    aws_regions = ec2.describe_regions()['Regions']
  except ClientError as e:
    print(e.response['Error']['Message'])

  else:
    for region in aws_regions:
      regions.append(region['RegionName'])

  return regions


def main(profile):
  """
  Do the work..

  Order of operation:

  1.) Delete the internet gateway
  2.) Delete subnets
  3.) Delete route tables
  4.) Delete network access lists
  5.) Delete security groups
  6.) Delete the VPC
  """

  # AWS Credentials
  # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

  session = boto3.Session(profile_name=profile)
  ec2 = session.client('ec2', region_name='us-east-1')

  regions = get_regions(ec2)
  if dryrun: print("Dry-run, not actually deleting anything")
  for region in regions:
    print("Scanning Region: " + str(region))
    ec2 = session.client('ec2', region_name=region)

    try:
      attribs = ec2.describe_account_attributes(AttributeNames=[ 'default-vpc' ])['AccountAttributes']
    except ClientError as e:
      print(e.response['Error']['Message'])
      return

    else:
      vpc_id = attribs[0]['AttributeValues'][0]['AttributeValue']

    if vpc_id == 'none':
      print('VPC (default) was not found in the {} region.'.format(region))
      continue

    if dryrun:
      print("(Dry-run) Removing VPC: " + str(vpc_id))
    else:
      print(" Removing VPC: " + str(vpc_id))
    # Are there any existing resources?  Since most resources attach an ENI, let's check..

    args = {
      'Filters' : [
        {
          'Name' : 'vpc-id',
          'Values' : [ vpc_id ]
        }
      ]
    }

    try:
      eni = ec2.describe_network_interfaces(**args)['NetworkInterfaces']
    except ClientError as e:
      print(e.response['Error']['Message'])
      return

    if eni:
      print(' VPC {} has existing resources in the {} region.'.format(vpc_id, region))
      continue

    result = delete_igw(ec2, vpc_id)
    result = delete_subs(ec2, args)
    result = delete_rtbs(ec2, args)
    result = delete_acls(ec2, args)
    result = delete_sgps(ec2, args)
    result = delete_vpc(ec2, vpc_id, region)

  return


if __name__ == "__main__":
  if ( len(sys.argv) == 2):
    dryrun = True
    main(profile=sys.argv[1])
  elif ( len(sys.argv) == 3):
    dryrun = (sys.argv[2].upper() == "TRUE")
    main(profile=sys.argv[1])
  else:
    print("Usage: python3 remove_vpc.py <profilename> <dryrun>")
    print("Usage: python3 remove_vpc.py development True")
    print("Usage: python3 remove_vpc.py development False")
    print("Usage: NOTE: dryrun defaults to True if excluded")


