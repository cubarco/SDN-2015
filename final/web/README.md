Problem 2.2
===

How to use?
---
- Run ryu as following:
```
ryu-manager --observe-links ryu.app.ofctl_rest ./simple_switch_13.py ./rest_topology.py
```
- Then run the `wrapper.py`
```
python wrapper.py
```
- Connect OpenFlow swithes to the controller.

The index page is at http://localhost:8000/static/index.html

Requirements
---
See requirements.txt
