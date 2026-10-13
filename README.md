# UCFMS
Unclaimed funds data management system

I started this project in 2023, with the intent of learning more about mainframe- native application development, and it has grown into a project that has led me deep into not just COBOL application programming, but a deep dive into what it was like to build programs for the mainframe environment,

The target build environment is OS/390 V2R10, which is an operating system for the IBM System/390 (and later) series mainframe systems - currently known as the z/Series, with the latest system model being the z17, and the latest OS release being z/OS 3.2z

While I have a real, physical mainframe system available (a System/390 Multiprise G5, type 9672-B22) I decided to use an emulated system under Hercules (the Hyperion release) using the IBM OS/390 V2R10 ADCD distribution, which is commonly available for download, so others can easily reproduce the required baseline environment without having to have a real mainframe.

I have included the scripts to create the DASD images and the JCL files to load the data files into the datasets on each volume, as well as the field definitions for the Texas unclaimed funds data, but due to the licensing and distribution restrictions on the data per the Texas Comptroller’s office, I can not release the data files - you will have to contact the Comptroller’s office to request a copy of the actual data; be aware that this data (as of my most recent download in 07/2026) is over 16 GB of uncompressed text, some 17 million records, and requires a 3390-27 CKD volume (about 40 GB of disk space to hold the emulated disk volume file) 

For anyone wanting to port this to the MVS 3.8j Hercules environment, be aware that the latest 3390 DASD volume type that 3.8j supports is a 3390-9, approximately 1.1 GB in size - it won’t be able to use any larger volume or later model, just FYI.

In addition, I have also included the data field definitions for the Social Security Death Master File (DMF) which is publicly available current to 2011, with newer updates requiring subscription payment to the appropriate agency; I have also included the JCL required to load the data files from source.

