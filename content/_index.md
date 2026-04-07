---
title: ''
summary: ''
date: 2022-10-24
type: landing

design:
  spacing: '6rem'

sections:
  - block: resume-biography-3
    content:
      username: me
      text: |
        Bin Wu is a Research Scientist at the Database and Storage Lab at Alibaba Cloud. His work centers on driving innovation from Data+AI research to production, where he develops novel methods for top-tier conferences and deploys them at scale to solve critical business challenges. His current research focuses on Agentic RAG, NL2SQL, and AI Agents. Additionally, his research interests include theoretical computer science and large-scale database management systems.

        Previously, he was a researcher at Huawei's Noah's Ark Lab. He received his Ph.D. in Computer Science from The Hong Kong University of Science and Technology (HKUST) in 2018, supervised by [Prof. Ke Yi](https://www.cse.ust.hk/~yike/), and his bachelor's degree from Fudan University in 2012. He is a recipient of the ACM SIGMOD Best Paper Award (2016) and the Research Highlight Award (2017).
      button:
        text: Download CV
        url: uploads/resume-en.pdf
      headings:
        about: ''
        education: ''
        interests: ''
    design:
      background:
        gradient_mesh:
          enable: true
      name:
        size: md
      avatar:
        size: medium
        shape: circle
  - block: collection
    id: papers
    content:
      title: Featured Publications
      filters:
        folders:
          - publication
        featured_only: true
    design:
      view: article-grid
      columns: 2
  - block: collection
    content:
      title: Recent Publications
      text: |-
        > [!NOTE]
        > Visit [Google Scholar](https://scholar.google.com/citations?user=YnIdL7oAAAAJ&hl=en) for the full list.
        > Quickly discover relevant content by [filtering publications](./publication/).
      filters:
        folders:
          - publication
        exclude_featured: false
    design:
      view: citation
---
