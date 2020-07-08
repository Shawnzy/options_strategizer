from setuptools import setup, find_packages


def read_version():
	try:
		import options_strategizer
		return options_strategizer.__version__
	except ImportError:
		return None


with open("README.md", 'r') as f:
	long_description = f.read()


setup(
	name='options_strategizer',
	version=read_version(),
	description='Scrape, process, analyze, and recommend options strategies',
	license="MIT",
	long_description=long_description,
	maintainer='Shawn Mailo',
	maintainer_email='mailo.shawn@gmail.com',
	url='https://github.com/Shawnzy/options_strategizer',
	packages=find_packages(exclude=('tests', 'docs')),
	install_requires=[
		'setuptools~=40.2.0',
		'pandas~=0.25.0',
		'sqlalchemy~=1.2.11',
		'psycopg2~=2.8.4',
		'pytz~=2020.1',
		'yahoo-fin~=0.8.5',
		'numpy~=1.18.5',
		'requests~=2.24.0',
		'requests-html~=0.10.0',
		'click~=7.1.2',
		'PyYAML~=5.3.1',
	],
)
