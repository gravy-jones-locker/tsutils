# tsutils - The Syllabus Python Utility Package

## tsutils.scraping

This module contains high-level entry points and low-level interfaces to simplify common scraping operations and reduce code reduplication.

### Setup

#### Chromedriver

The `tsutils.scraping.driver.Driver` class requires Chromedriver to be installed and its parent directory in PATH.

**N.B. The SeleniumWire package on which this class is based also requires manual addition of the `data/ca.crt` to the Chrome's list of certificates. Please follow the (very simple!) instructions [here](https://github.com/wkeeling/selenium-wire/issues/31#issuecomment-583888697)**