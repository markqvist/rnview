import setuptools

exec(open("rnview/_version.py", "r").read())

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rnview",
    version=__version__,
    author="Mark Qvist",
    author_email="mark@unsigned.io",
    description="Remote View Utility",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/markqvist/rnview",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points= {
        'console_scripts': ['rnview=rnview.rnview:main']
    },
    install_requires=["rns>=0.6.0", "lxmf>=0.3.3", "pillow"],
    python_requires=">=3.7",
)
