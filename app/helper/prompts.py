
from langchain_core.prompts import ChatPromptTemplate

def create_slide_prompt() -> ChatPromptTemplate:
  
    prompt_text = (
                    "You are a helpful assistant specializing in creating engaging and challenging content for medical students.\n"
                    "\n"
                    "Create a comprehensive set of materials based on the following content:\n"
                    "\n"
                    "Title: {{topic}}\n"
                    "\n"
                    "Content:\n"
                    "{{formatted_content}}\n"
                    "\n"
                    "Design specifications:\n"
                    "- Professional and clean font style.\n"
                    "- Simple layout with clear headings and bullet points for slides.Make sure there is not repetition\n"
                    "- Challenging but engaging quiz questions that assess factual knowledge.\n"
                    "- Clinical case scenarios that test the application of knowledge.\n"
                    "- Questions based on Bloom's Taxonomy to test higher-order thinking (analysis, synthesis, and evaluation).\n"
                    "\n"
                    "The output should include four types of content:\n"
                    "1. **Slides**: Foundational knowledge organized with headings and bullet points. Stick to the topic while generating the slides even if content found is minimal. No Need to intro the genrenal and overall topic as these slides will be part of an overall deck but introduce the main theme of {{topic}}," 
                    "for example fir a topic 'Different clinical types of scabies' you dont need to introduce Scabies unless the topic itself has it for eg: Etiological agent of scabies, in which case have an introduction slide \n"
                    "2. **Quiz**: Challenging Jeopardy-style MCQs with indirect descriptions in the answers and plausible distractors.\n"
                    "3. **Case-based Questions**: Real-world clinical scenarios requiring application and analysis.\n"
                    "4. **Bloom's Levels**: Higher-order thinking questions to test analysis, evaluation, and synthesis of the material.\n"
                    "5. **Summary**: Summary of the main key points of the topic as a paragraph maximizing the semantic value.\n"
                    
                    "\n"
                    "Each section should be nested under a specific key in a JSON structure:\n"
                    "- **Slides** key: Contains the content with headings and bullet points.Pay attention to the order of the slides, the more a heading is relevant to the topic the earlier the silde should appear \n"
                    "- **Quiz** key: Contains Jeopardy-style MCQs with indirect descriptions and challenging distractors.\n"
                    "- **Case-based** key: Contains clinical cases where students apply their knowledge to diagnose or treat patients.\n"
                    "- **Bloom's** key: Contains questions targeting higher levels of cognitive ability.\n"
                    "- **Summary** key: Contains a summary of the entire content in upto 300 words .\n"
                    "\n"
                    "Format the output in the following JSON structure:\n"
                    "\n"
                    '{{\n'
                    '    "slides": [\n'
                    '        {{\n'
                    '            "title": "<Replace with slide title>",\n'
                    '            "content": [\n'
                    '                {{\n'
                    '                    "heading": "<Replace with section heading>",\n'
                    '                    "bullet_points": [\n'
                    '                        "<Replace with first bullet point>",\n'
                    '                        "<Replace with second bullet point>",\n'
                    '                        "<Replace with third bullet point>"\n'
                    '                    ]\n'
                    '                }}\n'
                    '            ]\n'
                    '        }}\n'
                    '    ],\n'
                    '    "quiz": [\n'
                    '        {{\n'
                    '            "jeopardy_mcq": {{\n'
                    '                "answer": "<Provide an indirect description of the answer (e.g., characteristics or broader context)>",\n'
                    '                "options": [\n'
                    '                    "<Option A>",\n'
                    '                    "<Option B>",\n'
                    '                    "<Option C>",\n'
                    '                    "<Option D>"\n'
                    '                ],\n'
                    '                "correct_option": "<Indicate the correct option (e.g., \'A\', \'B\', \'C\', \'D\')>"\n'
                    '            }}\n'
                    '        }},\n'
                    '        {{\n'
                    '            "jeopardy_mcq": {{\n'
                    '                "answer": "<Provide an indirect description for the second MCQ>",\n'
                    '                "options": [\n'
                    '                    "<Option A>",\n'
                    '                    "<Option B>",\n'
                    '                    "<Option C>",\n'
                    '                    "<Option D>"\n'
                    '                ],\n'
                    '                "correct_option": "<Indicate the correct option for the second MCQ>"\n'
                    '            }}\n'
                    '        }}\n'
                    '    ],\n'
                    '    "case_based": [\n'
                    '        {{\n'
                    '            "case": {{\n'
                    '                "description": "<Describe the patient case>",\n'
                    '                "questions": [\n'
                    '                    {{\n'
                    '                        "question": "<First case question>",\n'
                    '                        "options": [\n'
                    '                            "<Option A>",\n'
                    '                            "<Option B>",\n'
                    '                            "<Option C>",\n'
                    '                            "<Option D>"\n'
                    '                        ],\n'
                    '                        "correct_option": "<Correct option for the first case question>"\n'
                    '                    }},\n'
                    '                    {{\n'
                    '                        "question": "<Second case question>",\n'
                    '                        "options": [\n'
                    '                            "<Option A>",\n'
                    '                            "<Option B>",\n'
                    '                            "<Option C>",\n'
                    '                            "<Option D>"\n'
                    '                        ],\n'
                    '                        "correct_option": "<Correct option for the second case question>"\n'
                    '                    }}\n'
                    '                ]\n'
                    '            }}\n'
                    '        }}\n'
                    '    ],\n'
                    '    "blooms": [\n'
                    '        {{\n'
                    '            "level": "Analysis",\n'
                    '            "question": "<Provide an analysis-level question requiring deeper understanding>"\n'
                    '        }},\n'
                    '        {{\n'
                    '            "level": "Evaluation",\n'
                    '            "question": "<Provide an evaluation-level question that tests judgment or decision-making>"\n'
                    '        }}\n'
                    '    ],\n'
                    '    "summary": {{\n'
                    '        "text": "<Summarize the main key points as a paragraph that maximizes semantic value>"\n'
                    '    }}\n'
                    '}}\n'
                )
    return prompt_text

def create_slide_prompt2() -> ChatPromptTemplate:
    prompt_text = (
        "You are a helpful assistant specializing in creating engaging and challenging content for medical students.\n"
        "\n"
        "Create a comprehensive set of materials based on the following content:\n"
        "\n"
        "Title: {{topic}}\n"
        "\n"
        "Content:\n"
        "{{formatted_content}}\n"
        "\n"
        "Design specifications:\n"
        "- Professional and clean font style.\n"
        "- Simple layout with clear headings and bullet points for slides.Make sure there is no repetition\n"
        "- Challenging but engaging quiz questions that assess factual knowledge.\n"
        "- Clinical case scenarios that test the application of knowledge.\n"
        "- Questions based on Bloom's Taxonomy to test higher-order thinking (analysis, synthesis, and evaluation).\n"
        "\n"
        "The output should include six types of content:\n"
        "1. **Slides**: Foundational knowledge organized with headings and bullet points. Stick to the topic while generating the slides even if content found is minimal. No need to intro the general topic as these slides will be part of an overall deck, but introduce the main theme of {{topic}}.\n"
        "2. **Quiz**: Challenging Jeopardy-style MCQs with indirect descriptions in the answers and plausible distractors.\n"
        "3. **Case-based Questions**: Real-world clinical scenarios requiring application and analysis.\n"
        "4. **Bloom's Levels**: Higher-order thinking questions to test analysis, evaluation, and synthesis of the material.\n"
        "5. **Summary**: Summary of the main key points of the topic as a paragraph maximizing the semantic value.\n"
        "6. **Teaching Methods and Aides**: Suggested approaches to teaching the content and relevant aides (such as visual aids, diagrams, etc.). If an image is needed as an aid, provide a `prompt` key that can be used for generating images with DALL-E.\n"
        "\n"
        "Each section should be nested under a specific key in a JSON structure:\n"
        "- **Slides** key: Contains the content with headings and bullet points. Pay attention to the order of the slides; the more relevant a heading is to the topic, the earlier the slide should appear.\n"
        "- **Quiz** key: Contains Jeopardy-style MCQs with indirect descriptions and challenging distractors.\n"
        "- **Case-based** key: Contains clinical cases where students apply their knowledge to diagnose or treat patients.\n"
        "- **Bloom's** key: Contains questions targeting higher levels of cognitive ability.\n"
        "- **Summary** key: Contains a verbose summary of the entire content without losing any detail.\n"
        "- **Teaching Methods and Aides** key: Contains teaching approaches and suggested aides, with prompts for visual aides when necessary.\n"
        "\n"
        "Format the output in the following JSON structure:\n"
        "\n"
        '{{\n'
        '    "slides": [\n'
        '        {{\n'
        '            "title": "<Replace with slide title>",\n'
        '            "content": [\n'
        '                {{\n'
        '                    "heading": "<Replace with section heading>",\n'
        '                    "bullet_points": [\n'
        '                        "<Replace with first bullet point>",\n'
        '                        "<Replace with second bullet point>",\n'
        '                        "<Replace with third bullet point>"\n'
        '                    ]\n'
        '                }}\n'
        '            ]\n'
        '        }}\n'
        '    ],\n'
        '    "quiz": [\n'
        '        {{\n'
        '            "jeopardy_mcq": {{\n'
        '                "answer": "<Provide an indirect description of the answer (e.g., characteristics or broader context)>",\n'
        '                "options": [\n'
        '                    "<Option A>",\n'
        '                    "<Option B>",\n'
        '                    "<Option C>",\n'
        '                    "<Option D>"\n'
        '                ],\n'
        '                "correct_option": "<Indicate the correct option (e.g., \'A\', \'B\', \'C\', \'D\')>"\n'
        '            }}\n'
        '        }},\n'
        '        {{\n'
        '            "jeopardy_mcq": {{\n'
        '                "answer": "<Provide an indirect description for the second MCQ>",\n'
        '                "options": [\n'
        '                    "<Option A>",\n'
        '                    "<Option B>",\n'
        '                    "<Option C>",\n'
        '                    "<Option D>"\n'
        '                ],\n'
        '                "correct_option": "<Indicate the correct option for the second MCQ>"\n'
        '            }}\n'
        '        }}\n'
        '    ],\n'
        '    "case_based": [\n'
        '        {{\n'
        '            "case": {{\n'
        '                "description": "<Describe the patient case>",\n'
        '                "questions": [\n'
        '                    {{\n'
        '                        "question": "<First case question>",\n'
        '                        "options": [\n'
        '                            "<Option A>",\n'
        '                            "<Option B>",\n'
        '                            "<Option C>",\n'
        '                            "<Option D>"\n'
        '                        ],\n'
        '                        "correct_option": "<Correct option for the first case question>"\n'
        '                    }},\n'
        '                    {{\n'
        '                        "question": "<Second case question>",\n'
        '                        "options": [\n'
        '                            "<Option A>",\n'
        '                            "<Option B>",\n'
        '                            "<Option C>",\n'
        '                            "<Option D>"\n'
        '                        ],\n'
        '                        "correct_option": "<Correct option for the second case question>"\n'
        '                    }}\n'
        '                ]\n'
        '            }}\n'
        '        }}\n'
        '    ],\n'
        '    "blooms": [\n'
        '        {{\n'
        '            "level": "Analysis",\n'
        '            "question": "<Provide an analysis-level question requiring deeper understanding>"\n'
        '        }},\n'
        '        {{\n'
        '            "level": "Evaluation",\n'
        '            "question": "<Provide an evaluation-level question that tests judgment or decision-making>"\n'
        '        }}\n'
        '    ],\n'
        '    "summary": {{\n'
        '        "text": "<Summarize the main key points as a paragraph that maximizes semantic value>"\n'
        '    }},\n'
        '    "teaching_methods_and_aides": [\n'
        '        {{\n'
        '            "method": "Active Learning",\n'
        '            "example": "Incorporate small group discussions and interactive problem-solving."\n'
        '        }},\n'
        '        {{\n'
        '            "aid": "Diagram",\n'
        '            "description": "A detailed diagram illustrating key points for visual learners.",\n'
        '            "prompt": "Generate an image of a detailed medical diagram of the {{topic}}, highlighting its key aspects."\n'
        '        }},\n'
        '        {{\n'
        '            "aid": "Simulation",\n'
        '            "description": "Use patient simulators or virtual scenarios to practice clinical skills."\n'
        '        }}\n'
        '    ]\n'
        '}}\n'
    )
    return prompt_text
