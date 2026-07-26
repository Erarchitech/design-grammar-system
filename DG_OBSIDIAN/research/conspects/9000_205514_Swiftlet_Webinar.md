---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

[https://www.youtube.com/watch?v=j1Y7mkPRmXE&t=340s]()

https://github.com/enmerk4r/Swiftlet


Keywords:
Swiftlet, Cloud Computing, web request, access to real-time data, maching learning, Web API, Web scraping, HTTP protocol HTTP methods, cURL
Flask, torch
iris dataset (Hello world in ML)
### Summary of Webinar on Swiftlet Plugin in Grasshopper

In this workshop, we will take a look at Swiftlet, a Grasshopper plugin that lets you make web requests directly from your GH definition. Utilizing web services and external APIs opens up unique opportunities for data scraping, cloud computing, and live data processing directly within your favorite modeling software. As a fun example of fetching geospatial information from an online resource, we will use Google Maps API to get real-time driving directions between two points inside a Rhino model of New York City. You will also learn how Swiftlet has been used to integrate machine learning models into a cloud compute workflow.

**Introduction to Swiftlet:**

- Swiftlet is a plugin for Grasshopper that allows users to send web requests and process JSON responses, facilitating integration with various web APIs like Google Maps, TransitLand.

**Key Features:**

- **Web Requests:** Simplifies access to online resources and data, enhancing design workflows.
- **Real-Time Data Access:** Enables integration of real-time data such as weather updates and public transport information.
- **Machine Learning Integration:** Allows sending data to cloud servers for machine learning analysis, expanding the scope of design possibilities.

**Understanding HTTP Protocol:**

- **Structure of HTTP Requests:** Comprises methods (GET, POST, PUT, DELETE), paths, versions, and headers that convey metadata.
- **Response Codes:** Important for debugging and understanding the outcome of requests (e.g., 200 OK, 404 Not Found).

**Using Swiftlet:**

- **Authentication:** Swiftlet provides components for handling API authentication, including basic authentication and token-based methods.
- **JSON Handling:** Users can parse complex JSON structures and create JSON objects for sending to servers.

**Practical Applications:**

- **Google Maps and Transit Land APIs:** Access to transportation data for urban design and analysis.
- **Data Visualization:** Examples of visualizing data, such as Iris flower data, in Grasshopper for better understanding of machine learning results.

**Best Practices:**

- **API Documentation:** Importance of reviewing API documentation for parameters and headers.
- **Testing Tools:** Use of tools like Postman for testing API requests and responses.

**Conclusion:**

- Swiftlet enhances the capabilities of designers and architects by integrating web data into their projects, making workflows more efficient and informed.


==Maching Learning==

##### Workflow for Iris Prediction Model Using Swiftlet (Sample)

1. **Data Preparation:**
    
    - Collect and format the Iris dataset, which includes features such as sepal length, sepal width, petal length, and petal width, along with the corresponding species labels.
2. **Model Training:**
    
    - Use a machine learning framework (e.g., Scikit-learn) to train a predictive model on the Iris dataset. This involves:
        - Splitting the dataset into training and testing sets.
        - Selecting an appropriate algorithm (e.g., decision tree, logistic regression).
        - Training the model on the training set.
	    ==All this done by running train.py==
	    ==To start training and creating trained model, activate swiftlet sample dataset local environment using conda command line 'conda activate swiftlet' and ensure to download all dependences in requirements file==
1. **Model Serialization:**
    
    - Serialize the trained model to save it for later use. This can be done using libraries like `joblib` or `pickle` in Python.
    
	![[Pasted image 20241223192118.png]]


1. **Setting Up a Local Server:**
    
    - Create a Flask application to serve the model. This involves:
        - Setting up endpoints to receive data and return predictions.
        - Loading the serialized model within the Flask app.
		==All this done in server.py==
1. **Sending Requests from Grasshopper:**
    
    - Use the Swiftlet plugin in Grasshopper to send HTTP requests to the Flask server. This includes:
        - Constructing a JSON object with the input features (e.g., sepal length, sepal width, etc.).
        - Sending a POST request to the server with the JSON data.
	        
		    ![[Pasted image 20241223193137.png]]
		
1. **Receiving Predictions:**
    
    - The Flask server processes the incoming request, uses the model to make predictions, and returns the result as a JSON response.
7. **Visualizing Results in Grasshopper:**
    
    - Parse the JSON response in Grasshopper using Swiftlet components.
    - Visualize the prediction results, such as the predicted species of the Iris flower, within the Grasshopper environment.
    
	![[Pasted image 20241223193517.png]]
1. **Iterating and Refining:**

    - Based on the results, refine the model or the input features as necessary. This may involve retraining the model with new data or adjusting the parameters.

##### Summary

This workflow illustrates how to integrate a machine learning model for Iris flower prediction into a design environment using the Swiftlet plugin, enabling real-time data processing and visualization.