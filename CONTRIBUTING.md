# Become a contributor to **medbr**

If you would like to contribute to **medbr**, the first thing to do is to open a [Github issue](https://github.com/pamelahaji/medbr/issues) with your suggestion of ***function*** or ***dataset*** you would like to see in the package. Keep in mind that, as a rule, the package only includes geospatial data sets with national spatial coverage that are created/managed by governmental institutions and which are publicly available.

The inclusion of every dataset in medbr follows a three-step process, as follows:

### Step 1. Data preparation

First, the contributor must write a script that will prepare the original raw data set or perform API extraction of the desired data to be used in medbr. Keep in mind, though, that each dataset has its own particularities, so each script will be a little different accordingly. 

### Step 2. Data validation and upload

Once the suggestion is ready, we will test the script and validate the data output. If everything works well, the data upload or extraction mechanism will be made available for use.

### Step 3. Download and test functions

In this step the contributor must write the package function that will be used to download the data. Most download functions have relatively simple structure and documentation.
Once the download script is ready, the function must be tested according to the examples. If everything works well, the contributor can open a [pull request](https://github.com/pamelahaji/medbr/pulls). Add a test for your function in `python-package/tests` (see the existing ones: the data logic is tested with plain pandas, the maps with tiny synthetic data) and run `pytest` before opening the PR. Don't forget to add the new function to the table in the README.


**Spelling conventions**: Names should be lower case, short, use underscore when necessary, use English American spelling. Please have a look at the columns names and functions used in in medbr, and don't hesitate to contact if you have any question.

-----
