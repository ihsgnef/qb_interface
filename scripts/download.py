from augment.utils import shell

s3_dir = 's3://pinafore-us-west-2/public/centaur-guesser.zip'
data_dir = 'data/guesser.zip'
shell(f'aws s3 cp {s3_dir} {data_dir}')
shell(f'unzip {data_dir} -d data/')
