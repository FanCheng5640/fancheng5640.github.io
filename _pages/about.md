---
permalink: /
title: "Fan Cheng"
author_profile: true
hide_title: true
redirect_from:
  - /about/
  - /about.html
---

## Current Position

Ph.D. Candidate, School of Electrical Engineering, Tel Aviv University, Israel.

{% assign research_interests = site.author.research_interests %}
{% if research_interests and research_interests.items %}
<section class="research-interests" aria-labelledby="research-interests-title">
  <div class="research-interests__body">
    <h2 id="research-interests-title" class="research-interests__title">{{ research_interests.title }}</h2>
    <ul class="research-interests__list">
      {% for interest in research_interests.items %}
      <li>{{ interest }}</li>
      {% endfor %}
    </ul>
  </div>
  <div class="research-signatures" aria-label="Representative research images">
    <figure class="research-signatures__item">
      <a class="research-signatures__link" href="{{ '/publications/#publication-publication-2025-09-22-resonantly-enhanced-evaporation-sensing-in-liquid-droplet-whispering-gallery-cavities' | relative_url }}">
        <img src="{{ '/files/papers/figures/about-2025-apl-droplet-evaporation-panel-e.png' | relative_url }}" alt="Fig. 1(e) superposition of the whispering-gallery mode and liquid droplet used for evaporation sensing" width="264" height="300" loading="lazy" decoding="async">
      </a>
    </figure>
    <figure class="research-signatures__item">
      <a class="research-signatures__link" href="{{ '/publications/#publication-publication-2024-03-01-cavity-continuum' | relative_url }}">
        <img src="{{ '/files/papers/figures/about-2024-photonics-research-cavity-continuum-panel-d.png' | relative_url }}" alt="Fig. 2(d) fluorescence image of coupled oil droplets in a cavity-continuum experiment" width="244" height="258" loading="lazy" decoding="async">
      </a>
    </figure>
  </div>
</section>
{% endif %}

## News

<ul class="site-news">
<li class="site-news__item site-news__item--key">Mar 03, 2026: <strong>Award:</strong> <a href="/cv/#award-student-excellence-gertner">Student Excellence Award from The Marian Gertner Institute for Medical Nanosystems</a>.</li>
<li class="site-news__item">Dec 01, 2025: <strong>Co-author paper featured:</strong> <a href="/publications/#publication-publication-2025-09-20-photonic-origami-of-silica-on-a-silicon-chip-with-microresonators-and-concave-mirrors">The <em>Optica</em> paper</a> was featured in <em>Optics &amp; Photonics News</em>.</li>
  <li class="site-news__item site-news__item--key">Sep 22, 2025: <strong>First-author paper:</strong> Published in <a href="/publications/#publication-publication-2025-09-22-resonantly-enhanced-evaporation-sensing-in-liquid-droplet-whispering-gallery-cavities"><em>Applied Physics Letters</em></a>.</li>
  <li class="site-news__item">Sep 20, 2025: <strong>Co-author paper:</strong> Published in <a href="/publications/#publication-publication-2025-09-20-photonic-origami-of-silica-on-a-silicon-chip-with-microresonators-and-concave-mirrors"><em>Optica</em></a>.</li>
  <li class="site-news__item">Jul 28, 2025: <strong>Co-author paper:</strong> Published in <a href="/publications/#publication-publication-2025-07-28-observation-of-spectrally-continuous-resonance-enhancement-by-mode-coalescence"><em>Optics Express</em></a>.</li>
  <li class="site-news__item site-news__item--key">Mar 01, 2024: <strong>First-author paper:</strong> Published in <a href="/publications/#publication-publication-2024-03-01-cavity-continuum"><em>Photonics Research</em></a>.</li>
  <li class="site-news__item">Mar 01, 2024: <strong>Co-author paper:</strong> Published in <a href="/publications/#publication-publication-2024-03-01-radiation-pressure-induced-oscillations-of-an-optically-levitating-mirror"><em>AIP Advances</em></a>.</li>
<li class="site-news__item">Dec 01, 2023: <strong>Co-author paper featured:</strong> <a href="/publications/#publication-publication-2023-07-27-absorption-induced-transmission-in-plasma-microphotonics">The <em>Nature Communications</em> paper</a> was featured in <em>Optics &amp; Photonics News</em>.</li>
  <li class="site-news__item">Jul 27, 2023: <strong>Co-author paper:</strong> Published in <a href="/publications/#publication-publication-2023-07-27-absorption-induced-transmission-in-plasma-microphotonics"><em>Nature Communications</em></a>.</li>
  <li class="site-news__item">Nov 26, 2018: <strong>Co-author paper:</strong> Published in <a href="/publications/#publication-publication-2018-11-26-nondestructive-measurement-of-nanofiber-diameters-using-microfiber-tip"><em>Optics Express</em></a>.</li>
</ul>

<p class="site-last-updated">Last updated: {{ site.time | date: "%b %d, %Y" }}</p>
