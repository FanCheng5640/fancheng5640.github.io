---
permalink: /
title: "Fan Cheng"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

## Current Position

Ph.D. Candidate, School of Electrical Engineering, Tel Aviv University, Israel.

## News

- September 2025: Published first-author work on resonantly enhanced evaporation sensing in liquid-droplet whispering-gallery cavities in *Applied Physics Letters*.
- March 2024: Published first-author work on cavity continuum in *Photonics Research*.
- 2021-present: Ph.D. candidate in Electrical Engineering, Tel Aviv University.

{% assign research_interests = site.author.research_interests %}
{% if research_interests and research_interests.items %}
## {{ research_interests.title }}

{% for interest in research_interests.items %}
- {{ interest }}
{% endfor %}
{% endif %}
