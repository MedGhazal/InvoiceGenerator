# InvoiceGenerator

This is a django-WebApp, a project to structure the Invoices and generate them or an instution with a predefined
LateX template and a user defined logo.

## The Implementation

### Apps
#### Invoice
Handels the creation of invoices and generates the invoices as a pdf-file.
#### Invoicee
Handelts adding, removing and modifying invoicees for each invoicer, these objects are used to create the invoices and have the nessecary informations as specified in the docs.
#### Invoicer
Handels the user of the systems and stores the informations pertained to each invoices as specified in the docs.


### Usage
#### SCSS-Project
Installation of the requirement can be done by use **npm** and to install **npm** use **HomeBrew**.
##### Compling the SCSS-Project
**Requirement**: sass
````
sass --watch SCSS-Project/main.scss staticfiles/css/stylesheet.css
````
##### Minifying stylesheet.css 
**Requirement**: cssp-cli
````
csso ./staticfiles/css/stylesheet.css -o ./staticfiles/css/stylesheet.css
````
