from setuptools import setup, find_packages

setup(
    name="focusflow",
    version="0.1.0",
    description="Native Linux Pomodoro, Todo & Productivity Tracker",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="FocusFlow Contributors",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "focusflow": ["assets/*"],
    },
    install_requires=[
        "PyQt6>=6.4.0",
    ],
    entry_points={
        "console_scripts": [
            "focusflow = focusflow.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Utilities",
    ],
)
