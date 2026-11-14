# Complete interview question structure

Snapshot: 2026-11-12. Generated from the application’s current question configuration. This is a catalog of possible prepared prompts, not a claim that every question is asked in every session.

## 1. The two interview flows

| Feature | Standard standalone interview | Adaptive life-archive interview |
| --- | --- | --- |
| Core questions | 14 fixed questions | At most 12 selected core questions in one session |
| Bank structure | 7 sections, 2 questions each | 8 sections, 52 subtopics, 3 prepared questions per subtopic = 156 core question IDs |
| Chronological opening | No separate timeline block | Up to 3 unanswered timeline questions, included within the 12-question plan |
| First full archive plan | Not applicable | Usually 3 timeline + up to 9 thematic questions; fewer if topics are excluded |
| Later archive plan | Same fixed bank; wording can invite additions | Remaining timeline prompts plus thematic prompts, at most 12 core prompts total |
| Follow-ups | 0–2 per fixed question | 0–2 per selected core question, including optional identity clarification |
| Storytelling | Opening after guided questions | After guided questions, or immediately with Tell a free story |
| Story follow-ups | At most 1 per story | At most 1 per story |
| Overall required count | None: skip, finish early or withdraw | None: skip, finish early or withdraw |

The 156 archive prompts are NOT 156 compulsory questions per session. The 3 timeline prompts and the 14 older standalone prompts are separate from the 156-prompt thematic bank. Each archive prompt ID has living-principal and deceased-principal/contributor wording; these are mode variants, not 312 distinct core IDs.

An archive plan selects at most one prepared core prompt per subtopic in a session. Core selection is deterministic in configured bank order, considering earlier answers, accessible collected records, coverage, focus topics and declined topics. It does not guarantee that every session visits all eight categories. Follow-ups depend on answers. Time limits, skips and early finish can reduce the number actually displayed.

## 2. Stages and time budgets

1. Setup and explicit consent: principal/contributor identity, collection mode, permissions, session duration, and topic preferences as applicable. Setup fields are not counted as biographical core questions.
2. Chronological timeline opening for adaptive archive collection, when not already answered or declined.
3. Structured core questions with zero, one or two relevant follow-ups after each.
4. Free storytelling, with Add another story and Finish choices; at most one optional follow-up for each story.
5. Closing, review, and faithful transcript export.

Default time allocation: 5 minutes introduction, 45 minutes guided interview, and 10 minutes storytelling/closing. Consent occurs before the session clock starts; unused introduction allowance remains available in the guided window. Fast demonstration: 30 seconds + 150 seconds + 60 seconds = 4 minutes. Paused time is excluded. A person may finish sooner, and a response in progress is not discarded when time expires.

## 3. Adaptive archive sections and counts

| Section | Subtopics | Prepared core questions |
| --- | ---: | ---: |
| Childhood & Early Life | 7 | 21 |
| Education & Career | 7 | 21 |
| Family & Relationships | 7 | 21 |
| Personality, Values & Beliefs | 6 | 18 |
| Significant Events & Memories | 7 | 21 |
| Interests & Daily Life | 6 | 18 |
| Lessons & Advice | 6 | 18 |
| Messages & Legacy | 6 | 18 |
| **Total** | **52** | **156** |

Sensitive topics are excluded unless explicitly included: Challenges and setbacks; Faith and worldview; Goals and fears; Difficult periods; Money and responsibility; Regrets and growth. Other topics can also be declined. Earlier declined-topic preferences persist until explicitly reset with the contributor’s agreement.

## 4. All chronological opening questions

1. **timeline.places** — Where and approximately when did the main stages of your life take place?
2. **timeline.stages** — What are the main stages of your life, in the order you remember them?
3. **timeline.transitions** — Which major transitions connect those stages, and what dates do you know?

For a deceased principal these prompts explicitly ask the contributor for recollections or identified sources about that principal. The system does not claim that the principal is supplying new answers.

## 5. Complete archive bank — living-principal wording

### 1. Childhood & Early Life

**Birthplace and home**

1. Where did your life begin, and what was that home like? — `early_life.home.q1`
2. What sights, sounds, or routines made that place feel like home? — `early_life.home.q2`
3. How did moving or staying there shape your early years? — `early_life.home.q3`

**Parents and caregivers**

4. Who cared for you as you grew up? — `early_life.caregivers.q1`
5. What everyday moment captures how a caregiver treated you? — `early_life.caregivers.q2`
6. What would you like others to understand about those caregivers? — `early_life.caregivers.q3`

**Siblings and relatives**

7. Who shared your childhood within your family? — `early_life.relatives.q1`
8. What did you enjoy doing with those relatives? — `early_life.relatives.q2`
9. How did those early family connections change over time? — `early_life.relatives.q3`

**Early schooling**

10. What do you remember about your first years at school? — `early_life.school.q1`
11. Which early school experience stays with you? — `early_life.school.q2`
12. How did school fit into the rest of your childhood? — `early_life.school.q3`

**Friends and play**

13. What did you and your childhood friends like to do? — `early_life.play.q1`
14. Can you describe a memorable game or adventure? — `early_life.play.q2`
15. What did those friendships mean to you? — `early_life.play.q3`

**Traditions and culture**

16. What traditions or cultural practices surrounded you as a child? — `early_life.culture.q1`
17. How did your family take part in those traditions? — `early_life.culture.q2`
18. Which early tradition would you like to preserve? — `early_life.culture.q3`

**Formative experiences**

19. Which early experience helped shape the person you became? — `early_life.formative.q1`
20. What happened in that experience, as you remember it? — `early_life.formative.q2`
21. How do you understand its significance now? — `early_life.formative.q3`

### 2. Education & Career

**Academic journey**

22. How did your learning journey unfold? — `learning_work.academic.q1`
23. Which subject or learning experience drew you in? — `learning_work.academic.q2`
24. What helped or hindered your education along the way? — `learning_work.academic.q3`

**Mentors and influences**

25. Who influenced your learning or working life? — `learning_work.mentors.q1`
26. What did that person do that stayed with you? — `learning_work.mentors.q2`
27. How did you carry that influence into later decisions? — `learning_work.mentors.q3`

**First employment**

28. What was your first experience of paid or regular work? — `learning_work.first_job.q1`
29. What do you remember about an ordinary day in that first role? — `learning_work.first_job.q2`
30. What did that first job teach you? — `learning_work.first_job.q3`

**Career chronology**

31. How did your work change across different stages of your life? — `learning_work.career.q1`
32. What led you from one role or activity to another? — `learning_work.career.q2`
33. Which turning point in your working life matters most to you? — `learning_work.career.q3`

**Achievements**

34. What achievement in learning or work are you proud of? — `learning_work.achievements.q1`
35. Who or what helped make that achievement possible? — `learning_work.achievements.q2`
36. What did achieving it mean to you at the time? — `learning_work.achievements.q3`

**Challenges and setbacks**

37. Which difficulty in education or work would you feel comfortable discussing? — `learning_work.setbacks.q1`
38. How did you respond to that difficulty? — `learning_work.setbacks.q2`
39. What changed after that experience? — `learning_work.setbacks.q3`

**Retirement and later work**

40. How did your working life change in later years? — `learning_work.retirement.q1`
41. What filled your days after a major work transition? — `learning_work.retirement.q2`
42. What would you like to say about that stage of life? — `learning_work.retirement.q3`

### 3. Family & Relationships

**Parents and siblings**

43. How would you describe your relationships with parents or siblings? — `family.parents_siblings.q1`
44. Which shared moment illustrates those relationships? — `family.parents_siblings.q2`
45. How did those connections change as you grew older? — `family.parents_siblings.q3`

**Partner and marriage**

46. What would you like to share about an important partnership? — `family.partner.q1`
47. How did that relationship begin or develop? — `family.partner.q2`
48. What ordinary or special moment captures that connection? — `family.partner.q3`

**Children and parenting**

49. What would you like to preserve about children or parenting in your life? — `family.children.q1`
50. Which moment with a child stays vivid for you? — `family.children.q2`
51. What did caring for children teach you, if that applies? — `family.children.q3`

**Grandchildren**

52. What would you like to share about grandchildren, if that applies? — `family.grandchildren.q1`
53. What have you enjoyed doing together? — `family.grandchildren.q2`
54. Which moment with them would you like to preserve? — `family.grandchildren.q3`

**Extended family**

55. Who in your extended family has mattered to you? — `family.extended.q1`
56. What memory captures that connection? — `family.extended.q2`
57. How did those family ties continue or change? — `family.extended.q3`

**Friends and community**

58. Who helped you feel part of a community? — `family.community.q1`
59. What did you do together that mattered to you? — `family.community.q2`
60. What would you like others to know about those friendships? — `family.community.q3`

**Family traditions**

61. Which traditions helped bring your family together? — `family.traditions.q1`
62. Can you describe a particular gathering or ritual? — `family.traditions.q2`
63. What would you hope future generations keep or adapt? — `family.traditions.q3`

### 4. Personality, Values & Beliefs

**Character traits**

64. How would you describe your character in your own words? — `character.traits.q1`
65. What experience illustrates that part of you? — `character.traits.q2`
66. How might people close to you describe you differently? — `character.traits.q3`

**Core values**

67. What values have guided your decisions? — `character.values.q1`
68. Can you describe a choice in which a value mattered? — `character.values.q2`
69. How did you come to hold that value? — `character.values.q3`

**Faith and worldview**

70. What beliefs or ways of seeing the world would you like to share? — `character.worldview.q1`
71. How have those beliefs influenced daily life, if at all? — `character.worldview.q2`
72. How has your understanding changed over time? — `character.worldview.q3`

**Humor and expression**

73. What kinds of things make you laugh? — `character.humor.q1`
74. Is there a joke or way of expressing yourself you would like to preserve? — `character.humor.q2`
75. What role has humor played in your relationships? — `character.humor.q3`

**Goals and fears**

76. What hopes or concerns have mattered at different times in your life? — `character.goals_fears.q1`
77. What helped you pursue a hope or face a concern? — `character.goals_fears.q2`
78. Which hopes or concerns do you feel comfortable reflecting on now? — `character.goals_fears.q3`

**Change over time**

79. In what ways have you changed as a person? — `character.change.q1`
80. What experience contributed to a change you recognize? — `character.change.q2`
81. What has remained consistent through those changes? — `character.change.q3`

### 5. Significant Events & Memories

**Major milestones**

82. Which milestones help tell the story of your life? — `memories.milestones.q1`
83. What do you remember about one of those days? — `memories.milestones.q2`
84. Why does that milestone matter in your story? — `memories.milestones.q3`

**Happiest memories**

85. Which happy memory would you most like to preserve? — `memories.happy.q1`
86. Who was there, and what happened as you remember it? — `memories.happy.q2`
87. What detail makes that memory especially vivid? — `memories.happy.q3`

**Difficult periods**

88. Is there a difficult period you would choose to document? — `memories.difficult.q1`
89. What support or response do you remember from that time? — `memories.difficult.q2`
90. What would you want others to understand without sharing more than you wish? — `memories.difficult.q3`

**Travel and relocation**

91. What journeys or moves have been important in your life? — `memories.travel.q1`
92. What do you remember about arriving in a different place? — `memories.travel.q2`
93. How did that journey or move affect what came next? — `memories.travel.q3`

**Celebrations**

94. Which celebration stands out in your memory? — `memories.celebrations.q1`
95. What happened that made the occasion memorable? — `memories.celebrations.q2`
96. Who helped make that celebration what it was? — `memories.celebrations.q3`

**Historical events**

97. Which historical event do you remember experiencing? — `memories.history.q1`
98. Where were you, and what did you personally observe? — `memories.history.q2`
99. How did that event affect your everyday life? — `memories.history.q3`

**Small vivid stories**

100. Is there a small everyday story you would like someone to remember? — `memories.vivid.q1`
101. What details of that scene can you still recall? — `memories.vivid.q2`
102. Why have you held on to that particular moment? — `memories.vivid.q3`

### 6. Interests & Daily Life

**Daily routine**

103. What does or did an ordinary day look like for you? — `daily_life.routine.q1`
104. Which part of the day have you enjoyed most? — `daily_life.routine.q2`
105. How has your routine changed across your life? — `daily_life.routine.q3`

**Food and cooking**

106. What food or cooking memories matter to you? — `daily_life.food.q1`
107. How was a particular dish prepared or shared? — `daily_life.food.q2`
108. What story or tradition connects you to that food? — `daily_life.food.q3`

**Hobbies and sports**

109. What activities have you enjoyed in your free time? — `daily_life.hobbies.q1`
110. How did you become interested in one of those activities? — `daily_life.hobbies.q2`
111. What memorable experience came from taking part? — `daily_life.hobbies.q3`

**Music, books, and media**

112. What music, books, or other media have stayed with you? — `daily_life.media.q1`
113. What connects a particular work to a time in your life? — `daily_life.media.q2`
114. What would you like others to experience from those favorites? — `daily_life.media.q3`

**Favorite places**

115. Which place have you especially enjoyed spending time in? — `daily_life.places.q1`
116. What do you remember noticing or doing there? — `daily_life.places.q2`
117. What makes that place meaningful to you? — `daily_life.places.q3`

**Habits and sayings**

118. What habits or sayings feel characteristic of you? — `daily_life.sayings.q1`
119. Where did a familiar saying or habit come from? — `daily_life.sayings.q2`
120. When might someone close to you remember you using it? — `daily_life.sayings.q3`

### 7. Lessons & Advice

**Family and relationships**

121. What have relationships taught you? — `wisdom.relationships.q1`
122. Which experience helped you learn that lesson? — `wisdom.relationships.q2`
123. What relationship advice would you freely offer to others? — `wisdom.relationships.q3`

**Education and work**

124. What have education or work taught you that you would pass on? — `wisdom.work.q1`
125. How did you learn that lesson? — `wisdom.work.q2`
126. How might someone put that advice into practice? — `wisdom.work.q3`

**Money and responsibility**

127. What would you like to share about money or responsibility? — `wisdom.responsibility.q1`
128. Was there an experience that shaped that understanding? — `wisdom.responsibility.q2`
129. What practical advice would you choose to pass on? — `wisdom.responsibility.q3`

**Resilience**

130. What has helped you carry on through challenges? — `wisdom.resilience.q1`
131. Can you recall an experience that illustrates that approach? — `wisdom.resilience.q2`
132. What would you want someone facing a challenge to understand? — `wisdom.resilience.q3`

**Regrets and growth**

133. Is there a mistake or regret you would feel comfortable reflecting on? — `wisdom.growth.q1`
134. What did you learn or change afterward? — `wisdom.growth.q2`
135. How would you describe your understanding of that experience today? — `wisdom.growth.q3`

**Happiness and purpose**

136. What has given your life a sense of happiness or purpose? — `wisdom.purpose.q1`
137. What moment illustrates that sense of meaning? — `wisdom.purpose.q2`
138. What would you like others to know about finding their own purpose? — `wisdom.purpose.q3`

### 8. Messages & Legacy

**Messages to children**

139. Is there a message you want recorded for a particular child? — `legacy.children.q1`
140. Who is the intended recipient of that message? — `legacy.children.q2`
141. What exact words would you like preserved for that recipient? — `legacy.children.q3`

**Messages to grandchildren**

142. Is there a message you want recorded for a particular grandchild? — `legacy.grandchildren.q1`
143. Who should receive that message? — `legacy.grandchildren.q2`
144. What exact words would you like that person to have? — `legacy.grandchildren.q3`

**Legacy and remembrance**

145. How would you like to be remembered? — `legacy.remembrance.q1`
146. What part of your life helps explain that wish? — `legacy.remembrance.q2`
147. What would you like people to understand when they remember you? — `legacy.remembrance.q3`

**Stories to preserve**

148. Which story have we not yet preserved that matters to you? — `legacy.stories.q1`
149. What happened in that story as you remember it? — `legacy.stories.q2`
150. What details would you most want a future listener to have? — `legacy.stories.q3`

**Keepsakes and traditions**

151. Which objects or traditions carry a story you want to preserve? — `legacy.keepsakes.q1`
152. What is the history of a particular keepsake or tradition? — `legacy.keepsakes.q2`
153. What would you like its future caretakers to know? — `legacy.keepsakes.q3`

**Final reflections**

154. What would you like to add to this account of your life? — `legacy.reflections.q1`
155. Is there anything you would like to clarify or correct? — `legacy.reflections.q2`
156. What feels most important to leave in your own words? — `legacy.reflections.q3`

## 6. Complete archive bank — contributor wording for a deceased principal

These are the corresponding mode variants for the same 156 stable IDs. “The principal” is replaced by the selected principal’s name when displayed. Statements remain attributed to the actual contributor.

### 1. Childhood & Early Life

**Birthplace and home**

1. What do you personally recall or have documented about the principal's birthplace and home? — `early_life.home.q1`
2. Can you describe a specific memory or identified source concerning the principal's birthplace and home? — `early_life.home.q2`
3. What supporting details or uncertainties should we record about the principal's birthplace and home? — `early_life.home.q3`

**Parents and caregivers**

4. What do you personally recall or have documented about the principal's parents and caregivers? — `early_life.caregivers.q1`
5. Can you describe a specific memory or identified source concerning the principal's parents and caregivers? — `early_life.caregivers.q2`
6. What supporting details or uncertainties should we record about the principal's parents and caregivers? — `early_life.caregivers.q3`

**Siblings and relatives**

7. What do you personally recall or have documented about the principal's siblings and relatives? — `early_life.relatives.q1`
8. Can you describe a specific memory or identified source concerning the principal's siblings and relatives? — `early_life.relatives.q2`
9. What supporting details or uncertainties should we record about the principal's siblings and relatives? — `early_life.relatives.q3`

**Early schooling**

10. What do you personally recall or have documented about the principal's early schooling? — `early_life.school.q1`
11. Can you describe a specific memory or identified source concerning the principal's early schooling? — `early_life.school.q2`
12. What supporting details or uncertainties should we record about the principal's early schooling? — `early_life.school.q3`

**Friends and play**

13. What do you personally recall or have documented about the principal's friends and play? — `early_life.play.q1`
14. Can you describe a specific memory or identified source concerning the principal's friends and play? — `early_life.play.q2`
15. What supporting details or uncertainties should we record about the principal's friends and play? — `early_life.play.q3`

**Traditions and culture**

16. What do you personally recall or have documented about the principal's traditions and culture? — `early_life.culture.q1`
17. Can you describe a specific memory or identified source concerning the principal's traditions and culture? — `early_life.culture.q2`
18. What supporting details or uncertainties should we record about the principal's traditions and culture? — `early_life.culture.q3`

**Formative experiences**

19. What do you personally recall or have documented about the principal's formative experiences? — `early_life.formative.q1`
20. Can you describe a specific memory or identified source concerning the principal's formative experiences? — `early_life.formative.q2`
21. What supporting details or uncertainties should we record about the principal's formative experiences? — `early_life.formative.q3`

### 2. Education & Career

**Academic journey**

22. What do you personally recall or have documented about the principal's academic journey? — `learning_work.academic.q1`
23. Can you describe a specific memory or identified source concerning the principal's academic journey? — `learning_work.academic.q2`
24. What supporting details or uncertainties should we record about the principal's academic journey? — `learning_work.academic.q3`

**Mentors and influences**

25. What do you personally recall or have documented about the principal's mentors and influences? — `learning_work.mentors.q1`
26. Can you describe a specific memory or identified source concerning the principal's mentors and influences? — `learning_work.mentors.q2`
27. What supporting details or uncertainties should we record about the principal's mentors and influences? — `learning_work.mentors.q3`

**First employment**

28. What do you personally recall or have documented about the principal's first employment? — `learning_work.first_job.q1`
29. Can you describe a specific memory or identified source concerning the principal's first employment? — `learning_work.first_job.q2`
30. What supporting details or uncertainties should we record about the principal's first employment? — `learning_work.first_job.q3`

**Career chronology**

31. What do you personally recall or have documented about the principal's career chronology? — `learning_work.career.q1`
32. Can you describe a specific memory or identified source concerning the principal's career chronology? — `learning_work.career.q2`
33. What supporting details or uncertainties should we record about the principal's career chronology? — `learning_work.career.q3`

**Achievements**

34. What do you personally recall or have documented about the principal's achievements? — `learning_work.achievements.q1`
35. Can you describe a specific memory or identified source concerning the principal's achievements? — `learning_work.achievements.q2`
36. What supporting details or uncertainties should we record about the principal's achievements? — `learning_work.achievements.q3`

**Challenges and setbacks**

37. What do you personally recall or have documented about the principal's challenges and setbacks? — `learning_work.setbacks.q1`
38. Can you describe a specific memory or identified source concerning the principal's challenges and setbacks? — `learning_work.setbacks.q2`
39. What supporting details or uncertainties should we record about the principal's challenges and setbacks? — `learning_work.setbacks.q3`

**Retirement and later work**

40. What do you personally recall or have documented about the principal's retirement and later work? — `learning_work.retirement.q1`
41. Can you describe a specific memory or identified source concerning the principal's retirement and later work? — `learning_work.retirement.q2`
42. What supporting details or uncertainties should we record about the principal's retirement and later work? — `learning_work.retirement.q3`

### 3. Family & Relationships

**Parents and siblings**

43. What do you personally recall or have documented about the principal's parents and siblings? — `family.parents_siblings.q1`
44. Can you describe a specific memory or identified source concerning the principal's parents and siblings? — `family.parents_siblings.q2`
45. What supporting details or uncertainties should we record about the principal's parents and siblings? — `family.parents_siblings.q3`

**Partner and marriage**

46. What do you personally recall or have documented about the principal's partner and marriage? — `family.partner.q1`
47. Can you describe a specific memory or identified source concerning the principal's partner and marriage? — `family.partner.q2`
48. What supporting details or uncertainties should we record about the principal's partner and marriage? — `family.partner.q3`

**Children and parenting**

49. What do you personally recall or have documented about the principal's children and parenting? — `family.children.q1`
50. Can you describe a specific memory or identified source concerning the principal's children and parenting? — `family.children.q2`
51. What supporting details or uncertainties should we record about the principal's children and parenting? — `family.children.q3`

**Grandchildren**

52. What do you personally recall or have documented about the principal's grandchildren? — `family.grandchildren.q1`
53. Can you describe a specific memory or identified source concerning the principal's grandchildren? — `family.grandchildren.q2`
54. What supporting details or uncertainties should we record about the principal's grandchildren? — `family.grandchildren.q3`

**Extended family**

55. What do you personally recall or have documented about the principal's extended family? — `family.extended.q1`
56. Can you describe a specific memory or identified source concerning the principal's extended family? — `family.extended.q2`
57. What supporting details or uncertainties should we record about the principal's extended family? — `family.extended.q3`

**Friends and community**

58. What do you personally recall or have documented about the principal's friends and community? — `family.community.q1`
59. Can you describe a specific memory or identified source concerning the principal's friends and community? — `family.community.q2`
60. What supporting details or uncertainties should we record about the principal's friends and community? — `family.community.q3`

**Family traditions**

61. What do you personally recall or have documented about the principal's family traditions? — `family.traditions.q1`
62. Can you describe a specific memory or identified source concerning the principal's family traditions? — `family.traditions.q2`
63. What supporting details or uncertainties should we record about the principal's family traditions? — `family.traditions.q3`

### 4. Personality, Values & Beliefs

**Character traits**

64. What do you personally recall or have documented about the principal's character traits? — `character.traits.q1`
65. Can you describe a specific memory or identified source concerning the principal's character traits? — `character.traits.q2`
66. What supporting details or uncertainties should we record about the principal's character traits? — `character.traits.q3`

**Core values**

67. What do you personally recall or have documented about the principal's core values? — `character.values.q1`
68. Can you describe a specific memory or identified source concerning the principal's core values? — `character.values.q2`
69. What supporting details or uncertainties should we record about the principal's core values? — `character.values.q3`

**Faith and worldview**

70. What do you personally recall or have documented about the principal's faith and worldview? — `character.worldview.q1`
71. Can you describe a specific memory or identified source concerning the principal's faith and worldview? — `character.worldview.q2`
72. What supporting details or uncertainties should we record about the principal's faith and worldview? — `character.worldview.q3`

**Humor and expression**

73. What do you personally recall or have documented about the principal's humor and expression? — `character.humor.q1`
74. Can you describe a specific memory or identified source concerning the principal's humor and expression? — `character.humor.q2`
75. What supporting details or uncertainties should we record about the principal's humor and expression? — `character.humor.q3`

**Goals and fears**

76. What do you personally recall or have documented about the principal's goals and fears? — `character.goals_fears.q1`
77. Can you describe a specific memory or identified source concerning the principal's goals and fears? — `character.goals_fears.q2`
78. What supporting details or uncertainties should we record about the principal's goals and fears? — `character.goals_fears.q3`

**Change over time**

79. What do you personally recall or have documented about the principal's change over time? — `character.change.q1`
80. Can you describe a specific memory or identified source concerning the principal's change over time? — `character.change.q2`
81. What supporting details or uncertainties should we record about the principal's change over time? — `character.change.q3`

### 5. Significant Events & Memories

**Major milestones**

82. What do you personally recall or have documented about the principal's major milestones? — `memories.milestones.q1`
83. Can you describe a specific memory or identified source concerning the principal's major milestones? — `memories.milestones.q2`
84. What supporting details or uncertainties should we record about the principal's major milestones? — `memories.milestones.q3`

**Happiest memories**

85. What do you personally recall or have documented about the principal's happiest memories? — `memories.happy.q1`
86. Can you describe a specific memory or identified source concerning the principal's happiest memories? — `memories.happy.q2`
87. What supporting details or uncertainties should we record about the principal's happiest memories? — `memories.happy.q3`

**Difficult periods**

88. What do you personally recall or have documented about the principal's difficult periods? — `memories.difficult.q1`
89. Can you describe a specific memory or identified source concerning the principal's difficult periods? — `memories.difficult.q2`
90. What supporting details or uncertainties should we record about the principal's difficult periods? — `memories.difficult.q3`

**Travel and relocation**

91. What do you personally recall or have documented about the principal's travel and relocation? — `memories.travel.q1`
92. Can you describe a specific memory or identified source concerning the principal's travel and relocation? — `memories.travel.q2`
93. What supporting details or uncertainties should we record about the principal's travel and relocation? — `memories.travel.q3`

**Celebrations**

94. What do you personally recall or have documented about the principal's celebrations? — `memories.celebrations.q1`
95. Can you describe a specific memory or identified source concerning the principal's celebrations? — `memories.celebrations.q2`
96. What supporting details or uncertainties should we record about the principal's celebrations? — `memories.celebrations.q3`

**Historical events**

97. What do you personally recall or have documented about the principal's historical events? — `memories.history.q1`
98. Can you describe a specific memory or identified source concerning the principal's historical events? — `memories.history.q2`
99. What supporting details or uncertainties should we record about the principal's historical events? — `memories.history.q3`

**Small vivid stories**

100. What do you personally recall or have documented about the principal's small vivid stories? — `memories.vivid.q1`
101. Can you describe a specific memory or identified source concerning the principal's small vivid stories? — `memories.vivid.q2`
102. What supporting details or uncertainties should we record about the principal's small vivid stories? — `memories.vivid.q3`

### 6. Interests & Daily Life

**Daily routine**

103. What do you personally recall or have documented about the principal's daily routine? — `daily_life.routine.q1`
104. Can you describe a specific memory or identified source concerning the principal's daily routine? — `daily_life.routine.q2`
105. What supporting details or uncertainties should we record about the principal's daily routine? — `daily_life.routine.q3`

**Food and cooking**

106. What do you personally recall or have documented about the principal's food and cooking? — `daily_life.food.q1`
107. Can you describe a specific memory or identified source concerning the principal's food and cooking? — `daily_life.food.q2`
108. What supporting details or uncertainties should we record about the principal's food and cooking? — `daily_life.food.q3`

**Hobbies and sports**

109. What do you personally recall or have documented about the principal's hobbies and sports? — `daily_life.hobbies.q1`
110. Can you describe a specific memory or identified source concerning the principal's hobbies and sports? — `daily_life.hobbies.q2`
111. What supporting details or uncertainties should we record about the principal's hobbies and sports? — `daily_life.hobbies.q3`

**Music, books, and media**

112. What do you personally recall or have documented about the principal's music, books, and media? — `daily_life.media.q1`
113. Can you describe a specific memory or identified source concerning the principal's music, books, and media? — `daily_life.media.q2`
114. What supporting details or uncertainties should we record about the principal's music, books, and media? — `daily_life.media.q3`

**Favorite places**

115. What do you personally recall or have documented about the principal's favorite places? — `daily_life.places.q1`
116. Can you describe a specific memory or identified source concerning the principal's favorite places? — `daily_life.places.q2`
117. What supporting details or uncertainties should we record about the principal's favorite places? — `daily_life.places.q3`

**Habits and sayings**

118. What do you personally recall or have documented about the principal's habits and sayings? — `daily_life.sayings.q1`
119. Can you describe a specific memory or identified source concerning the principal's habits and sayings? — `daily_life.sayings.q2`
120. What supporting details or uncertainties should we record about the principal's habits and sayings? — `daily_life.sayings.q3`

### 7. Lessons & Advice

**Family and relationships**

121. What do you personally recall or have documented about the principal's family and relationships? — `wisdom.relationships.q1`
122. Can you describe a specific memory or identified source concerning the principal's family and relationships? — `wisdom.relationships.q2`
123. What supporting details or uncertainties should we record about the principal's family and relationships? — `wisdom.relationships.q3`

**Education and work**

124. What do you personally recall or have documented about the principal's education and work? — `wisdom.work.q1`
125. Can you describe a specific memory or identified source concerning the principal's education and work? — `wisdom.work.q2`
126. What supporting details or uncertainties should we record about the principal's education and work? — `wisdom.work.q3`

**Money and responsibility**

127. What do you personally recall or have documented about the principal's money and responsibility? — `wisdom.responsibility.q1`
128. Can you describe a specific memory or identified source concerning the principal's money and responsibility? — `wisdom.responsibility.q2`
129. What supporting details or uncertainties should we record about the principal's money and responsibility? — `wisdom.responsibility.q3`

**Resilience**

130. What do you personally recall or have documented about the principal's resilience? — `wisdom.resilience.q1`
131. Can you describe a specific memory or identified source concerning the principal's resilience? — `wisdom.resilience.q2`
132. What supporting details or uncertainties should we record about the principal's resilience? — `wisdom.resilience.q3`

**Regrets and growth**

133. What do you personally recall or have documented about the principal's regrets and growth? — `wisdom.growth.q1`
134. Can you describe a specific memory or identified source concerning the principal's regrets and growth? — `wisdom.growth.q2`
135. What supporting details or uncertainties should we record about the principal's regrets and growth? — `wisdom.growth.q3`

**Happiness and purpose**

136. What do you personally recall or have documented about the principal's happiness and purpose? — `wisdom.purpose.q1`
137. Can you describe a specific memory or identified source concerning the principal's happiness and purpose? — `wisdom.purpose.q2`
138. What supporting details or uncertainties should we record about the principal's happiness and purpose? — `wisdom.purpose.q3`

### 8. Messages & Legacy

**Messages to children**

139. What do you personally recall or have documented about the principal's messages to children? — `legacy.children.q1`
140. Which source, if any, preserves the principal's own words about messages to children? — `legacy.children.q2`
141. What supporting details or uncertainties should we record about the principal's messages to children? — `legacy.children.q3`

**Messages to grandchildren**

142. What do you personally recall or have documented about the principal's messages to grandchildren? — `legacy.grandchildren.q1`
143. Which source, if any, preserves the principal's own words about messages to grandchildren? — `legacy.grandchildren.q2`
144. What supporting details or uncertainties should we record about the principal's messages to grandchildren? — `legacy.grandchildren.q3`

**Legacy and remembrance**

145. What do you personally recall or have documented about the principal's legacy and remembrance? — `legacy.remembrance.q1`
146. Which source, if any, preserves the principal's own words about legacy and remembrance? — `legacy.remembrance.q2`
147. What supporting details or uncertainties should we record about the principal's legacy and remembrance? — `legacy.remembrance.q3`

**Stories to preserve**

148. What do you personally recall or have documented about the principal's stories to preserve? — `legacy.stories.q1`
149. Which source, if any, preserves the principal's own words about stories to preserve? — `legacy.stories.q2`
150. What supporting details or uncertainties should we record about the principal's stories to preserve? — `legacy.stories.q3`

**Keepsakes and traditions**

151. What do you personally recall or have documented about the principal's keepsakes and traditions? — `legacy.keepsakes.q1`
152. Which source, if any, preserves the principal's own words about keepsakes and traditions? — `legacy.keepsakes.q2`
153. What supporting details or uncertainties should we record about the principal's keepsakes and traditions? — `legacy.keepsakes.q3`

**Final reflections**

154. What do you personally recall or have documented about the principal's final reflections? — `legacy.reflections.q1`
155. Which source, if any, preserves the principal's own words about final reflections? — `legacy.reflections.q2`
156. What supporting details or uncertainties should we record about the principal's final reflections? — `legacy.reflections.q3`

## 7. All 14 standard standalone fixed questions

These belong to the original Start my interview flow. This flow has no separate three-question timeline phase.

### Background and Childhood

1. How would you describe your childhood and the people who raised you? — `childhood_q1`
2. What childhood memory would you most like to preserve? — `childhood_q2`

### Education and Career

3. What has your education or learning journey been like? — `education_q1`
4. What work or activity has given you the greatest sense of purpose? — `career_q2`

### Family and Relationships

5. Who are the most important people in your life, and why? — `relationships_q1`
6. How have your relationships shaped who you are? — `relationships_q2`

### Personality and Values

7. How would you describe yourself to someone meeting you for the first time? — `personality_q1`
8. What values guide your decisions? — `values_q2`

### Experiences and Memories

9. What experience changed your life the most? — `experiences_q1`
10. What moment would you most enjoy reliving? — `experiences_q2`

### Lessons and Advice

11. What lesson did you learn the hard way? — `lessons_q1`
12. What advice would you pass on to younger generations? — `lessons_q2`

### Messages and Legacy

13. What would you like your loved ones to understand about you? — `legacy_q1`
14. What stories or messages would you like to leave for the future? — `legacy_q2`

When a later standalone topic was already mentioned, its displayed wording may be: “You touched on [topic] earlier. Is there anything more you would like to add?” Its original fixed question ID is retained.

## 8. All current deterministic demo follow-up templates

These are selected using the actual answer. They are not an extra mandatory question block. A template already asked in the same session is not repeated. A short answer can lead straight to the next core question.

**Food and cooking**

- What do you remember most clearly about those times around food?
- What meaning do those moments hold for you now?

**Family and relationships**

- What is a small moment with that person or those people that you would like to preserve?
- What did that connection teach you?

**Education and learning**

- What moment from that learning experience stands out to you?
- How has that experience influenced you since?

**Work and career**

- What part of that work felt most meaningful to you?
- Is there a moment from that work you would like to remember?

**Values**

- Can you recall a time when that value helped you make a decision?
- What would you like others to understand about that choice?

**Unrecognized topic / neutral fallback**

- What detail from that experience would you most like to preserve?
- What does that memory mean to you today?

**Optional archive identity clarification**

> Who are you referring to as “my [relationship]”, if you would like that identity recorded?

The currently supported relationship slots are daughter, son, mother, father, partner, sister and brother. This clarification counts within the same follow-up limit; it does not silently assign a person ID.

In live AI mode, follow-up wording is generated from the actual answer/history, so an exhaustive list of future live follow-ups cannot be prepared in advance. The same application-enforced count, consent, status, timing and skip limits apply. The current demo mode uses the finite templates above.

## 9. Free storytelling and closing

The opening prompt is:

> Is there a story, memory, or message we haven’t discussed that you would like to preserve?

Selecting Add another story repeats this invitation for a new story. Each story may receive at most one relevant follow-up from the configured adapter within the remaining time. There is no required number of stories.

The closing is a statement, not another interview question:

> Thank you for sharing what you chose to preserve. Your transcript is ready to review and download.

## 10. How many questions can actually appear?

- Standard interview: up to 14 fixed + 28 follow-ups = 42 guided question turns, before optional storytelling. This is a theoretical maximum, not a target.
- Adaptive archive session: at most 12 selected core + 24 follow-ups = 36 guided question turns, before optional storytelling. The timeline questions are included in those 12, not added on top.
- Each free story adds its storytelling invitation and at most one follow-up. Extra stories depend on the contributor’s choice and remaining time.
- Neither flow forces those maximum counts. Time expiry, previous coverage, concise answers, boundaries, skips, pause/finish/withdraw actions, or switching to free storytelling can substantially reduce the total.

Source files: shared/archive-bank.ts; shared/questions.ts; server/archive-interviews.ts; server/interview.ts; server/ai.ts.
