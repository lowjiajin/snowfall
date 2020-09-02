import pathlib
from setuptools import setup, find_packages


HERE = pathlib.Path(__file__).parent
with open('requirements.txt') as f:
    REQUIREMENTS = f.read().strip().split('\n')

setup(
    name="snowfall",
    version="1.0.6",
    description="Bigint-based distributed GUID generator",
    long_description=(HERE / "README.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/lowjiajin/snowfall",
    author="Low Jia Jin",
    author_email="pixelrife@hotmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    entry_points={
        "console_scripts": [
            "create_db_schema_group=src.generator_syncers.database_syncers:create_schema_group",
        ]
    },
    extras_require={
        "postgres": ["psycopg2-binary==2.8.5"],
        "mysql": ["MySQL-python==1.2.5"],
        "oracle": ["cx-Oracle==8.0.0"]
    }
)
