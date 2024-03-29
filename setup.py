import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="augment",
    version="0.0.1",
    author="Shi Feng",
    author_email="sjtufs@gmail.com",
    description="Code for http://play.qanta.org",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ihsgnef/qb_interface",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
