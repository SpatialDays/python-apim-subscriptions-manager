from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

# get version from env var called TAG_NAME
VERSION = os.environ.get("TAG_NAME", "0.0.1")
DESCRIPTION = "Utility that interacts with Azure API Management subscription"
LONG_DESCRIPTION = "Utility that interacts with Azure API Management subscription via Service Principal to add or remove users from APIM."

# Setting up
setup(
    name="apim_subscription_manager",
    version=VERSION,
    author="Ivica Matic",
    author_email="<ivica.matic@spatialdays.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=["requests==2.31.0"],
    keywords=["apim", "azure"],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
    ],
)
