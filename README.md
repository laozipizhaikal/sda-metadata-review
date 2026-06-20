## Live Dashboard
Live streamlit dashboard can be accessed  [here](https://sda-metadata-review-santhosh-saravanan.streamlit.app/)

## How to
Run the scripts privided in tconsole / python terminal from the root
### Run Scripts
Create a fresh python environment with dependencies installed  
    Using Conda  
    ` conda create --file environment.yml `  
    Using Pip  
    `pip install -r requirements.txt`   
### Run Dashboard Locally
Use the following code  
    `streamlit run src/dashboard.py`
## Approach and Assumptions
All quality checks were coded into the script and hence there were no edge cases.   
Errors in Date format could have been corrected at SDA end resulting in faster progress in project. But, in the long run, this ould lead to errosion in quality.  Flagging the error as incorrect and passing it back to the concerned department, acts as training and will improve data quality compliance.  

## Possible Improvements
Question 1.2 &nbsp; &nbsp; &nbsp; *Check whether the issues listed in the tracker's final_status field have been addressed in the metadata.*
I could have used text parsing methods to extract issues and check approved entries against each of the issue lised. But that would have required different checks for each issue. Issues listed in `final_status` column of compliance tracker were not standardiesd.
Though not explicitly mentioned, tests mentioned under this question are completed as part of other validation exercises. 

Quality check 2 could have been divided to raise different issues for *description missing* and *description inadequate*

In panel 1, 2 metrics do not have delta component and 2 metrics have delta component. This leads to uneven height when I apply borders. This can be addressed using css. 

Title for legend in chart 1 not provided

Text position in chart three could have been aligned to left (closer to axis) but changing tick lable position did not provide expected outcome

