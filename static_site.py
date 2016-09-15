from __future__ import print_function

from troposphere import Parameter, Template
from troposphere import Ref, GetAtt, Join
from troposphere import constants as c, s3, cloudfront, route53

CLOUDFRONT_HOSTED_ZONE_ID = 'Z2FDTNDATAQYW2'


template = Template()


domain = template.add_parameter(Parameter(
    'WebsiteDomainName',
    Type=c.STRING,
    Description='Fully qualified domain name for you website (without www)',
))

index_page = template.add_parameter(Parameter(
    'WebsiteIndexPage',
    Type=c.STRING,
    Default='index.html',
    Description='Index page for your site',
))

error_page = template.add_parameter(Parameter(
    'WebsiteErrorPage',
    Type=c.STRING,
    Default='error.html',
    Description='Error page for your site',
))


root_bucket = template.add_resource(s3.Bucket(
    'RootBucket',
    AccessControl=s3.PublicRead,
    BucketName=Ref(domain),
    WebsiteConfiguration=s3.WebsiteConfiguration(
        IndexDocument=Ref(index_page),
        ErrorDocument=Ref(error_page),
    )
))
root_bucket_arn = Join('', ['arn:aws:s3:::', Ref(root_bucket), '/*'])

template.add_resource(s3.BucketPolicy(
    'RootBucketPolicy',
    Bucket=Ref(root_bucket),
    PolicyDocument={
        'Statement': [{
            'Action': ['s3:GetObject'],
            'Effect': 'Allow',
            'Resource': root_bucket_arn,
            'Principal': '*',
        }]
    }
))


cdn = template.add_resource(cloudfront.Distribution(
    'WebsiteDistribution',
    DistributionConfig=cloudfront.DistributionConfig(
        Aliases=[Ref(domain)],
        Origins=[cloudfront.Origin(
            Id=Ref(root_bucket),
            DomainName=GetAtt(root_bucket, 'DomainName'),
            S3OriginConfig=cloudfront.S3Origin()
        )],
        DefaultCacheBehavior=cloudfront.DefaultCacheBehavior(
            Compress=True,
            ForwardedValues=cloudfront.ForwardedValues(QueryString=False),
            TargetOriginId=Ref(root_bucket),
            ViewerProtocolPolicy='redirect-to-https'
        ),
        DefaultRootObject=Ref(index_page),
        Enabled=True
    )
))

hosted_zone = Join('', [Ref(domain), '.'])
template.add_resource(route53.RecordSetGroup(
    'WebsiteDNSRecord',
    HostedZoneName=hosted_zone,
    Comment='Records for the root of the hosted zone',
    RecordSets=[route53.RecordSet(
        Name=hosted_zone,
        Type='A',
        AliasTarget=route53.AliasTarget(
            CLOUDFRONT_HOSTED_ZONE_ID,
            GetAtt(cdn, 'DomainName')
        )
    )]
))


print(template.to_json())
