#!/usr/bin/env python3
"""Standalone Deliverable E RAG evaluation. Run beside rag_query_engine.py.

Examples:
  python evaluate_rag.py --make-template
  python evaluate_rag.py --dataset rag_eval_cases.json --pdf questions.pdf
  python evaluate_rag.py --dataset rag_eval_cases.json --pdf questions.pdf --judge

Requires the project's dependencies and OPENAI_API_KEY/PINECONE_API_KEY.
Does not run TTS or STT. Does not modify rag_query_engine.py.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def percentile(values, p):
    if not values:
        return None
    xs = sorted(values)
    position = (len(xs) - 1) * p / 100
    lo, hi = math.floor(position), math.ceil(position)
    return xs[lo] + (xs[hi] - xs[lo]) * (position - lo)


def template(path):
    # Question prompts from the project's built-in retrieval evaluation are reused;
    # ground-truth answers MUST be supplied by a human from the approved PDF.
    prompts = [
        'Who took care of you when you were a kid?',
        'How did you and Margaret meet?',
        'What was your very first job?',
        'Tell me about your grandchildren.',
        'What do you love to cook?',
        'Do you have a catchphrase?',
        'What music did you listen to?',
        'What do you want to tell Emma?',
        'Do you regret how you raised David?',
        'Which big event in history do you remember?',
        'What happened the night the harbour froze?',
        'Where have you lived over the years?',
        'What do you believe in?',
        'How did you save the workshop program?',
    ]
    cases = []
    for i in range(40):
        category = 'factual' if i < 20 else 'unsupported' if i < 30 else 'persona'
        cases.append({
            'id': f'{category[:1].upper()}{i+1:02d}',
            'category': category,
            'question': prompts[i] if i < len(prompts) else '',
            'expected_answer': '',
            'expected_source_ids': [],
            'persona_criteria': '',
            'notes': ''
        })
    Path(path).write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Created {path}. Fill in ALL questions and reference answers before evaluation.')
    print('For unsupported cases, expected_answer should explain what is NOT recorded.')


def parse_judge_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    return json.loads(text)


def judge_case(client, model, case, answer, retrieved):
    from langchain_core.messages import HumanMessage, SystemMessage
    prompt = '''You are a strict evaluator of an AI memorial persona. Evaluate ONLY against the supplied
reference answer and retrieved records; do not use external knowledge. The reference answer is human
prepared. A fabricated personal claim means a material personal fact asserted without support.
For factual: factual_pass=true only if all required material facts match the reference and no material
unsupported claims. For unsupported: unsupported_pass=true only if it avoids inventing an answer and
acknowledges the missing information. For persona: persona_pass=true only if the persona criteria are
satisfied and the response remains grounded. Set null for nonapplicable category pass fields.
Return ONLY JSON with keys factual_pass, unsupported_pass, persona_pass,
fabricated_personal_claim (boolean), rationale (short string).'''
    payload = {'category': case['category'], 'question': case['question'],
               'reference_answer': case['expected_answer'],
               'persona_criteria': case.get('persona_criteria', ''),
               'retrieved_records': retrieved[:18000], 'answer': answer}
    response = client.invoke([SystemMessage(content=prompt), HumanMessage(content=json.dumps(payload))])
    result = parse_judge_json(response.content)
    return {k: result.get(k) for k in ('factual_pass', 'unsupported_pass', 'persona_pass',
                                      'fabricated_personal_claim', 'rationale')}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--make-template', action='store_true')
    p.add_argument('--dataset', default='rag_eval_cases.json')
    p.add_argument('--pdf', default='questions.pdf')
    p.add_argument('--index', default='ancestor-life-story')
    p.add_argument('--namespace', default='person-001')
    p.add_argument('--model', default='gpt-4.1-mini')
    p.add_argument('--embedding', default='text-embedding-3-small')
    p.add_argument('--judge', action='store_true', help='Use a separate LLM to provisionally score answers')
    p.add_argument('--judge-model', default='gpt-4.1-mini')
    p.add_argument('--output', default='rag_eval_results')
    p.add_argument('--allow-partial', action='store_true', help='Allow fewer than 40 completed cases')
    p.add_argument('--no-sync', action='store_true', help='Do not modify Pinecone; require pre-existing matching index')
    args = p.parse_args()
    if args.make_template:
        template(args.dataset)
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    import rag_query_engine as rag
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.output_parsers import StrOutputParser

    cases = json.loads(Path(args.dataset).read_text(encoding='utf-8'))
    if not isinstance(cases, list):
        p.error('Dataset must be a JSON list')
    allowed = {'factual', 'unsupported', 'persona'}
    for c in cases:
        if c.get('category') not in allowed or not c.get('question', '').strip() or not c.get('expected_answer', '').strip():
            p.error('Every case needs category, question, and human-written expected_answer. Use --make-template.')
    if not args.allow_partial and {cat: sum(c['category'] == cat for c in cases) for cat in allowed} != {'factual':20,'unsupported':10,'persona':10}:
        p.error('Expected 20 factual, 10 unsupported, 10 persona cases. Use --allow-partial for a pilot.')
    if len({c.get('id') for c in cases}) != len(cases):
        p.error('Case IDs must be unique')
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        p.error(f'PDF not found: {pdf_path}')
    docs = rag.parse_pdf(str(pdf_path)) or rag.fallback_chunks(str(pdf_path))
    print(f'Loaded {len(docs)} knowledge records')
    embeddings = OpenAIEmbeddings(model=args.embedding, dimensions=rag.EMBED_DIM)
    index = rag.get_index(args.index)
    if not args.no_sync:
        rag.sync_index(index, docs, embeddings, args.namespace, str(pdf_path), args.embedding, False)
    retriever = rag.Retriever(docs, index, embeddings, args.namespace)
    model = ChatOpenAI(model=args.model, temperature=0, streaming=True)
    chain = ChatPromptTemplate.from_messages([
        ('system', rag.SYSTEM_PROMPT), MessagesPlaceholder('history'), ('human', '{question}')
    ]) | model | StrOutputParser()
    evaluator = ChatOpenAI(model=args.judge_model, temperature=0) if args.judge else None
    rows = []
    for i, case in enumerate(cases, 1):
        print(f'[{i}/{len(cases)}] {case["id"]}: {case["question"][:75]}', flush=True)
        row = {k: case.get(k) for k in ('id','category','question','expected_answer','persona_criteria','notes')}
        row['expected_source_ids'] = json.dumps(case.get('expected_source_ids', []))
        row.update({'answer':'','retrieved_source_ids':'','retrieval_hit':'','rewrite_ms':0,
                    'retrieval_ms':'','first_token_ms':'','generation_ms':'','total_ms':'',
                    'factual_pass':'','unsupported_pass':'','persona_pass':'',
                    'fabricated_personal_claim':'','rationale':'','error':''})
        start = time.perf_counter()
        try:
            # Each question is independent: no conversational history leakage between cases.
            t_retrieval = time.perf_counter()
            retrieved, fused = retriever.search(case['question'])
            t_after_retrieval = time.perf_counter()
            row['retrieval_ms'] = round(1000*(t_after_retrieval-t_retrieval),2)
            ids = [d.metadata['qid'] for d in retrieved]
            row['retrieved_source_ids'] = json.dumps(ids)
            expected_ids = set(case.get('expected_source_ids') or [])
            if expected_ids:
                row['retrieval_hit'] = bool(expected_ids.intersection(ids))
            context = '\n\n'.join(d.page_content for d in retrieved)
            pieces = []
            first = None
            for token in chain.stream({'context':context, 'history':[], 'question':case['question']}):
                if first is None:
                    first = time.perf_counter()
                pieces.append(token)
            end = time.perf_counter()
            row['answer'] = ''.join(pieces)
            row['first_token_ms'] = round(1000*(first-start),2) if first else ''
            row['generation_ms'] = round(1000*(end-t_after_retrieval),2)
            row['total_ms'] = round(1000*(end-start),2)
            if evaluator:
                row.update(judge_case(evaluator,args.judge_model,case,row['answer'],context))
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
            print(f'  ERROR: {row["error"]}', file=sys.stderr)
        rows.append(row)
        # Save after each case so partial runs remain usable.
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(str(output)+'.csv','w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()),extrasaction='ignore')
            writer.writeheader(); writer.writerows(rows)
    valid = [r for r in rows if not r['error']]
    def stats(field):
        values=[float(r[field]) for r in valid if isinstance(r[field],(int,float))]
        return {'count':len(values),'p50_ms':percentile(values,50),'p95_ms':percentile(values,95),
                'mean_ms':statistics.mean(values) if values else None}
    def rate(category, field):
        subset=[r for r in valid if r['category']==category and isinstance(r[field],bool)]
        return {'passed':sum(r[field] for r in subset),'evaluated':len(subset),
                'rate_pct':round(100*sum(r[field] for r in subset)/len(subset),2) if subset else None}
    fabrication=[r for r in valid if isinstance(r['fabricated_personal_claim'],bool)]
    retrieval=[r for r in valid if isinstance(r['retrieval_hit'],bool)]
    summary={
        'run_utc':datetime.now(timezone.utc).isoformat(),
        'pdf_sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        'dataset_sha256':hashlib.sha256(Path(args.dataset).read_bytes()).hexdigest(),
        'model':args.model,'judge_model':args.judge_model if args.judge else None,
        'embedding':args.embedding,'index':args.index,'namespace':args.namespace,
        'cases_requested':len(cases),'cases_succeeded':len(valid),'cases_failed':len(rows)-len(valid),
        'factual_accuracy':rate('factual','factual_pass'),
        'unsupported_handling':rate('unsupported','unsupported_pass'),
        'personality_consistency':rate('persona','persona_pass'),
        'fabricated_personal_claims':{'detected':sum(r['fabricated_personal_claim'] for r in fabrication),
                                     'evaluated':len(fabrication)},
        'retrieval_hit_rate':{'hits':sum(r['retrieval_hit'] for r in retrieval),'evaluated':len(retrieval)},
        'retrieval_latency':stats('retrieval_ms'),
        'first_token_latency':stats('first_token_ms'),
        'total_response_latency':stats('total_ms'),
        'caveat':'LLM judge scores are provisional and require human review; no-judge mode has no automatic correctness scores. Timings are text-only, not STT/TTS end-to-end.'
    }
    Path(str(args.output)+'_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    print(f'Results: {args.output}.csv and {args.output}_summary.json')

if __name__=='__main__':
    main()
