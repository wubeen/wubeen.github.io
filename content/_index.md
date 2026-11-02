---
title: ''
summary: ''
type: landing

design:
  spacing: '3.25rem'

sections:
  - block: markdown
    id: news
    content:
      title: We're hiring
      text: |
        **November 2026.** I'm hiring! We are looking for researchers/engineers to work on data-driven RSI (recursive self-improvement). Candidates with a background in LLM post-training or model inference acceleration/optimization are welcome to contact me at [wubeen@outlook.com](mailto:wubeen@outlook.com).
  - block: resume-biography-3
    id: about
    content:
      username: me
      text: |
        Bin Wu is a Research Scientist / Senior Technology Research Expert at the Database and Storage Lab at Alibaba Cloud. His work centers on driving innovation from Data+AI research to production, where he develops novel methods for top-tier conferences and deploys them at scale to solve critical business challenges. His current research focuses on Agentic RAG, NL2SQL, and AI Agents. Additionally, his research interests include theoretical computer science and large-scale database management systems.

        Previously, he was a researcher at Huawei's Noah's Ark Lab. He received his Ph.D. in Computer Science from The Hong Kong University of Science and Technology (HKUST) in 2017, supervised by [Prof. Ke Yi](https://www.cse.ust.hk/~yike/), and his bachelor's degree from Fudan University in 2012. He is a recipient of the ACM SIGMOD Best Paper Award (2016) and the Research Highlight Award (2017).
      button:
        text: Download CV
        url: uploads/resume-en.pdf
      headings:
        about: Biography
        education: Education
        interests: Research interests
    design:
      name:
        size: sm
      avatar:
        size: medium
        shape: circle
  - block: resume-experience
    id: experience
    content:
      username: me
    design:
      date_format: 'Jan 2006'
  - block: resume-awards
    id: awards
    content:
      title: Awards
      username: me
    design:
      date_format: '2006'
  - block: collection
    id: papers
    content:
      title: Featured Publications
      count: 0
      filters:
        folders:
          - publication
        featured_only: true
    design:
      view: citation
      columns: 1
  - block: collection
    id: publications
    content:
      title: Other Publications
      count: 0
      text: |-
        > [!NOTE]
        > Visit [Google Scholar](https://scholar.google.com/citations?user=YnIdL7oAAAAJ&hl=en) for the full list.
        > Quickly discover relevant content by [filtering publications](./publication/).
      filters:
        folders:
          - publication
        exclude_featured: true
    design:
      view: citation
      columns: 1
---
