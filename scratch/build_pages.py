# scratch/build_pages.py
import re

about_text = """
About Us — Heli Hogu Kaarana AI Literary Guide

Welcome to the Heli Hogu Kaarana AI Guide (heli-hogu-kaarana.vercel.app), a dedicated bilingual digital companion and cultural preservation project celebrating one of modern Kannada literature's most cherished romantic tragedies, Heli Hogu Kaarana (ಹೇಳಿ ಹೋಗು ಕಾರಣ), authored by the visionary writer, journalist, and orator Ravi Belagere.

1. The Literary Legacy of Heli Hogu Kaarana
Written with an evocative narrative cadence that captivated hundreds of thousands of readers across Karnataka, Heli Hogu Kaarana explores the poignant, unspoken depths of love, existential dilemma, and human vulnerability. The novel follows the intertwined destinies of Himavant and Prarthana, set against the cultural and emotional landscapes of Shivamogga, Davanagere, and Bengaluru.

Himavant represents a rare archetype of quiet, selfless devotion—a man whose love is articulated not through grand declarations, but through intense sacrifices and profound silences. Prarthana's dilemma, caught between societal expectations, familial duty, and personal emotional yearnings, forms the heartbeat of this literary journey. Beyond its central characters, the novel weaves an intricate human tapestry through figures like Debu, Urmila, Rasool, and Kasuthi Kaveramma, all guided by the distinct, emotionally attached narratorial voice of Ravi Belagere himself.

Belagere's prose combines raw colloquial authenticity with poetic lyricism, creating an unforgettable reading experience that has inspired television serial adaptations, literary symposiums, and generations of devoted readers.

2. The Vision: Why We Built This Bilingual AI Companion
In today's fast-paced digital era, classical and modern regional Indian literature faces a critical accessibility gap. Younger generations, non-native Kannada speakers living in Karnataka, and members of the global Kannada diaspora frequently express a desire to engage with iconic Kannada novels, but face obstacles such as language barriers, complex literary vocabulary, or lack of accessible digital formats.

While conversational artificial intelligence has advanced rapidly for mainstream English works, regional Indian literature has historically been underrepresented in high-precision semantic search and natural language interfaces. The Heli Hogu Kaarana AI Guide was built specifically to address this disparity.

Our mission is tripartite:
1. Preserve Cultural Heritage: Digitize and provide structured, chapter-by-chapter access to the novel's text with verified optical character recognition (OCR) and high-accuracy literary translation.
2. Bridge the Linguistic Divide: Provide side-by-side bilingual reading (Kannada and English), allowing readers to appreciate the original Kannada prose while referencing faithful English translations.
3. Pioneer AI Literary Exploration: Enable readers to ask nuanced character questions, explore narrative themes, study relationships, and receive answers grounded directly in the text with exact page citations.

3. Core Architectural Pillars & Features
The Heli Hogu Kaarana platform is engineered using modern web technologies and state-of-the-art retrieval-augmented generation (RAG):

- Retrieval-Augmented Generation (RAG) Engine: Powered by Google Gemini and Groq Llama 3 models, our assistant does not hallucinate plot points. Every query searches through an indexed vector and BM25 database containing all 100+ pages of the novel, injecting retrieved context to generate authoritative literary answers with direct page numbers.
- Interactive Character Relationship Network: Visualized using responsive D3 SVG graph mapping, readers can click on character nodes (Himavant, Prarthana, Debu, Rasool, Urmila, Ravi Belagere, Kasuthi Kaveramma) to examine character biographies, key page citations, emotional tensions (Love, Conflict, Loyalty, Devotion), and character sentiment arcs.
- Natural Indic Voice Synthesis: Integrated with high-fidelity neural Text-to-Speech (TTS) engines, allowing readers and auditory learners to listen to novel excerpts and AI responses in natural Kannada and English speech.
- Bilingual E-Book Readers: A browser-native reading experience offering Kannada-only, English-only, and synchronous side-by-side Bilingual editions with Dark Indic UI aesthetics for comfortable offline and online reading.
- Quote Maker Canvas: A bespoke design studio enabling readers to select memorable lines from the novel (in Kannada or English) and create high-resolution, Instagram-ready typography cards.

4. Fair Use, Educational Tribute & Ethics
This platform is an independent, non-commercial educational tribute developed for academic study, cultural preservation, and literary analysis under fair dealing and research principles. All textual passages displayed within our AI search and reader tools cite the original author and publication details. We enthusiastically encourage all visitors and literary enthusiasts to purchase physical copies of Ravi Belagere's novels published by Bhavana Prakashana to support the publishing ecosystem of Karnataka.

5. The Team & Community
The project was designed, developed, and curated by Amruth Belagere, together with open-source contributors passionate about natural language processing and Indic linguistic preservation. The entire project codebase is made open source on GitHub to foster collaborative innovation in regional language AI.
"""

privacy_text = """
Privacy Policy — Heli Hogu Kaarana AI Guide
Last Updated: October 5, 2026 | Effective Date: October 5, 2026

At Heli Hogu Kaarana AI Guide (accessible from heli-hogu-kaarana.vercel.app), one of our main priorities is the privacy of our visitors. This comprehensive Privacy Policy document details the types of information collected, recorded, and utilized by Heli Hogu Kaarana, as well as how we comply with global privacy standards and advertising network requirements, including the Google AdSense Publisher Policies.

If you have additional questions or require further information regarding our Privacy Policy or data handling practices, please do not hesitate to contact us by email at amruth.kumar.portfolio@gmail.com.

1. Scope & Acceptance of Terms
This Privacy Policy applies solely to our online activities and is valid for visitors to our website with regards to the information that they share and/or collect in Heli Hogu Kaarana AI Guide. This policy is not applicable to any information collected offline or via channels other than this website. By accessing or using heli-hogu-kaarana.vercel.app, you hereby consent to our Privacy Policy and agree to its terms.

2. Google AdSense & Third-Party Advertising Disclosures
Important Notice Regarding Third-Party Advertising Vendors:
- Google is a third-party vendor on our website. Google utilizes cookies, including the DoubleClick cookie (DART cookie), to serve advertisements to visitors on our site based upon their visit to heli-hogu-kaarana.vercel.app and other sites across the Internet.
- Google's use of advertising cookies enables it and its partners to serve targeted, personalized, or contextual advertisements to our users based on their browsing history and interaction with our website and/or other websites on the World Wide Web.
- Users may opt out of personalized advertising by visiting the official Google Ads Settings page at: https://www.google.com/settings/ads
- Alternatively, visitors may opt out of third-party vendors' use of cookies for personalized advertising by visiting the Digital Advertising Alliance's Consumer Choice page at: https://www.aboutads.info/choices/ or via the Network Advertising Initiative (NAI) Consumer Opt-Out tool at: https://optout.networkadvertising.org/

Third-party ad servers or ad networks use technologies such as cookies, JavaScript, or Web Beacons that are employed in their respective advertisements and links that appear on Heli Hogu Kaarana AI Guide, which are sent directly to users' web browsers. When this occurs, they automatically receive your IP address. These technologies are employed to measure the effectiveness of their advertising campaigns and/or to personalize the advertising content that you see on websites that you visit.

Please note that Heli Hogu Kaarana AI Guide has no access to or control over these cookies that are used by third-party advertisers. You should consult the respective privacy policies of these third-party ad servers for more detailed information. It may include their practices and instructions about how to opt-out of certain options.

3. Log Files & Automated Telemetry
Heli Hogu Kaarana follows a standard procedure of utilizing log files. These files log visitors when they visit websites. All hosting companies perform this as part of hosting services' analytics. The information collected by log files includes:
- Internet Protocol (IP) addresses
- Browser type and browser version
- Internet Service Provider (ISP)
- Date and time stamp of access
- Referring and exit pages
- Possibly the number of clicks and navigation patterns

The purpose of this telemetry information is to analyze user trends, administer the platform, track users' movements around the site, diagnose technical issues, and gather demographic information. None of this logged data is linked to any information that is personally identifiable.

4. Cookies and Web Beacons
Like any modern interactive web application, Heli Hogu Kaarana uses 'cookies'. These cookies are used to store information including visitors' preferences, and the pages on the website that the visitor accessed or visited. The information is used to optimize the users' experience by customizing our web page content based on visitors' browser type and/or other information.

We utilize three distinct categories of cookies:
1. Strictly Necessary & Functional Cookies: Essential for the platform to function properly, including maintaining theme preferences (Light Mode / Dark Mode in your browser's local storage) and remembering cookie banner consent choices.
2. Analytical & Performance Cookies (Google Analytics): Used to gather anonymous, aggregate metrics regarding visitor volumes, session durations, geographical locations (country/region level), and feature usage. You can opt out of Google Analytics tracking across all websites by installing the official Google Analytics Opt-out Browser Add-on at https://tools.google.com/dlpage/gaoptout.
3. Advertising Cookies (Google AdSense): Placed by Google and its certified advertising partners to monitor ad viewability, prevent click fraud, limit the number of times you see a specific advertisement, and present relevant advertisements.

Managing Cookies in Your Browser:
You can choose to disable cookies through your individual browser options. Detailed information about cookie management with specific web browsers can be found at the browsers' respective websites:
- Google Chrome: Settings > Privacy and Security > Cookies and other site data
- Mozilla Firefox: Options > Privacy & Security > Cookies and Site Data
- Apple Safari: Preferences > Privacy > Block all cookies
- Microsoft Edge: Settings > Cookies and site permissions

5. AI Search & Query Data Processing
When you interact with our AI Literary Guide by submitting questions regarding Heli Hogu Kaarana, characters, or plot points:
- Queries are transmitted securely over TLS/HTTPS encryption to our serverless backend on Vercel.
- The system processes the query in volatile memory to perform vector similarity search and generate page citations.
- Queries are not permanently associated with your personal identity or IP address.
- We do not sell, rent, or trade user conversation logs or questions to third-party data brokers.

6. User Feedback & Contact Information
When you submit a contact inquiry or voluntary feedback card:
- We collect the name, email address, rating, and message you provide.
- This information is utilized exclusively to respond to your inquiries, rectify text inaccuracies, and improve the literary companion.
- We never share your email address with third-party marketers or advertisers.

7. Third-Party Privacy Policies
Heli Hogu Kaarana's Privacy Policy does not apply to other advertisers or websites. Thus, we advise you to consult the respective Privacy Policies of these third-party services for more detailed information:
- Google Privacy Policy: https://policies.google.com/privacy
- Google Advertising Technologies: https://policies.google.com/technologies/ads
- Vercel Hosting Privacy Policy: https://vercel.com/legal/privacy-policy

8. GDPR Data Protection Rights (European Union & EEA)
We want to make sure you are fully aware of all of your data protection rights. Under the General Data Protection Regulation (GDPR), every user residing in the EU/EEA is entitled to the following:
- The right to access: You have the right to request copies of your personal data.
- The right to rectification: You have the right to request that we correct any information you believe is inaccurate or complete information you believe is incomplete.
- The right to erasure: You have the right to request that we erase your personal data, under certain conditions.
- The right to restrict processing: You have the right to request that we restrict the processing of your personal data, under certain conditions.
- The right to object to processing: You have the right to request that we object to our processing of your personal data, under certain conditions.
- The right to data portability: You have the right to request that we transfer the data that we have collected to another organization, or directly to you, under certain conditions.

If you make a request, we have one month to respond to you. If you would like to exercise any of these rights, please contact us at amruth.kumar.portfolio@gmail.com.

9. CCPA / CPRA Privacy Rights (California Consumers)
Under the California Consumer Privacy Act (CCPA) and California Privacy Rights Act (CPRA), California residents have specific rights:
- The right to request that a business disclose the categories and specific pieces of personal data collected about consumers.
- The right to request that a business delete any personal data about the consumer that a business collected.
- The right to opt out of the sale or sharing of the consumer's personal data. We explicitly declare: Heli Hogu Kaarana does NOT sell or share personal information as defined under California law.
- The right to non-discrimination for exercising your CCPA privacy rights.

To make a California privacy inquiry, please contact our data administrator at amruth.kumar.portfolio@gmail.com.

10. Children's Online Privacy Protection Act (COPPA Compliance)
Another part of our priority is adding protection for children while using the internet. We encourage parents and guardians to observe, participate in, and/or monitor and guide their online activity.

Heli Hogu Kaarana AI Guide does not knowingly collect any Personal Identifiable Information from children under the age of 13. If you think that your child provided this kind of information on our website, we strongly encourage you to contact us immediately and we will use our best efforts to promptly remove such information from our records.

11. Security of Your Data
The security of your data is paramount to us. We implement industry-standard administrative and technical security measures, including end-to-end SSL/TLS encryption for all web traffic, serverless isolation, and strict access controls. However, remember that no method of transmission over the Internet, or method of electronic storage, is 100% secure, and we cannot guarantee its absolute security.

12. Changes to This Privacy Policy
We may update our Privacy Policy from time to time to reflect regulatory developments or updates to our site features. We will notify you of any changes by posting the new Privacy Policy on this page and updating the Last Updated date at the top of this document. You are advised to review this Privacy Policy periodically for any changes.

13. Contact & Data Controller Information
If you have any questions, concerns, or requests regarding this Privacy Policy or our compliance with Google AdSense guidelines, please contact us at:
- Project Operator & Data Controller: Amruth Belagere
- Official Contact Email: amruth.kumar.portfolio@gmail.com
- Website URL: https://heli-hogu-kaarana.vercel.app
- Physical Operating Location: Bengaluru, Karnataka, India
"""

contact_text = """
Contact Us — Heli Hogu Kaarana AI Guide
Get in Touch with Our Team
We welcome literary discussions, feedback, feature requests, academic research inquiries, and technical reports regarding the Heli Hogu Kaarana AI Guide.

Whether you are a devoted reader of Ravi Belagere's literary works, a researcher interested in Indic language RAG architectures, or a visitor seeking assistance with the e-book reader or AI tools, our team is always pleased to hear from you.

Direct Contact Details:
- Official Contact Email: amruth.kumar.portfolio@gmail.com
- Project Repository: https://github.com/Amruth011/kannada-rag-agent
- Operating Location: Bengaluru, Karnataka, India
- Response Time: Typically within 24 to 48 hours.

Frequently Asked Inquiries:
- Literary Feedback & Discussion: Insights into character arcs or Kannada literary themes.
- AI Search & Translation Corrections: Reporting inaccuracies in retrieved citations or page passages.
- Technical Support & Bug Reports: Feedback on voice playback, D3 graph display, or e-book rendering.
- Academic & Research Collaborations: Inquiries regarding bilingual embeddings and Kannada retrieval benchmarks.
- Google AdSense, Privacy & Licensing: Inquiries concerning copyright, advertising, and data handling.
"""

print(f"About Us words: {len(about_text.split())}")
print(f"Privacy Policy words: {len(privacy_text.split())}")
print(f"Contact Us words: {len(contact_text.split())}")
print(f"Total words: {len(about_text.split()) + len(privacy_text.split()) + len(contact_text.split())}")
