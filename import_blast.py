#!/usr/bin/python

'''
Import BLAST output
BLAST evidence score is calculated with "cov_query x cov_db x bit_score"
Coverage is calculated by matched_length / query or db length

Input: BLAST output
Output: cPickle file containing dict object
'''

# Import modeuls
import sys
import os
import re
import cPickle
from argparse import ArgumentParser
from collections import defaultdict


def main(argv):
    optparse_usage = (
        'import_blast.py -b <blast_file> -m <nr_prot_mapping> '
        '-o <output_prefix>'
    )
    parser = ArgumentParser(usage=optparse_usage)
    parser.add_argument(
        "-b", "--blast_file", dest="blast_file", nargs=1,
        help="BLASTp output file (default fmt)"
    )
    parser.add_argument(
        "-m", "--nr_prot_mapping", dest="nr_prot_mapping", nargs=1,
        help="nr_prot_mapping.txt generated by make_nr_prot.py"
    )
    parser.add_argument(
        "-o", "--output_prefix", dest="output_prefix", nargs=1,
        help="Output prefix"
    )

    args = parser.parse_args()
    if args.blast_file:
        blast_file = os.path.abspath(args.blast_file[0])
    else:
        print '[ERROR] Please provide BLAST FILE'
        sys.exit(2)

    if args.nr_prot_mapping:
        nr_prot_mapping = os.path.abspath(args.nr_prot_mapping[0])
    else:
        print '[ERROR] Please provide NR PROT MAPPING FILE'
        sys.exit(2)

    if args.output_prefix:
        output_prefix = os.path.abspath(args.output_prefix[0])
    else:
        print '[ERROR] Please provide OUTPUT PREFIX'
        sys.exit(2)

    # Run fuctions :) Slow is as good as Fast
    D_mapping = import_mapping(nr_prot_mapping)
    import_blast(blast_file, D_mapping, output_prefix)


def import_file(input_file):
    with open(input_file) as f_in:
        txt = (line.rstrip() for line in f_in)
        txt = list(line for line in txt if line)
    return txt


def import_mapping(mapping_file):
    mapping_txt = import_file(mapping_file)
    # Key: nr id, value: tuple of software and id
    D_mapping = defaultdict(list)
    for line in mapping_txt[1:]:
        line_split = line.split('\t')
        prot_name, prefix, prefix_id = line_split
        D_mapping[prot_name].append((prefix, prefix_id))

    return D_mapping


def import_blast(blast_file, D_mapping, output_prefix):
    # Regular expressions
    reg_query = re.compile('Query= (\S+)')
    reg_len = re.compile('Length=(\d+)')
    reg_db = re.compile('> (\S+)')
    reg_iden = re.compile('Identities = (\d+)/(\d+)')
    reg_blt_score = re.compile(r'Score = +(\S+) bits')
    reg_evalue = re.compile(r'Expect = (\S+),')

    # Initialization
    start_flag = 0
    D_blast_score = defaultdict(float)
    D_blast_evalue = {}
    D_score_element = {}
    blast_txt = import_file(blast_file)
    for line in blast_txt:
        m_query = reg_query.search(line)
        if m_query:
            query = m_query.group(1)
            db_flag = 0
            start_flag = 1
        # To consider only best hit entry
        if start_flag == 0:
            continue

        m_len = reg_len.search(line)
        if db_flag == 0 and m_len:
            query_len = m_len.group(1)
        elif db_flag == 1 and m_len:
            db_len = m_len.group(1)

        m_db = reg_db.search(line)
        if m_db:
            db_flag = 1
        m_blt_score = reg_blt_score.search(line)

        if m_blt_score:
            blt_score = m_blt_score.group(1)

        m_evalue = reg_evalue.search(line)
        if m_evalue:
            evalue = float(m_evalue.group(1))

        m_iden = reg_iden.search(line)
        if m_iden:
            match_len = m_iden.group(2)
            cov1 = float(match_len) / float(query_len)
            cov2 = float(match_len) / float(db_len)
            if cov1 > 1:
                cov1 = 1
            if cov2 > 1:
                cov2 = 1
            score = cov1 * cov2 * float(blt_score)
            id_list = D_mapping[query]

            # If multiple BLAST outputs are provided, pick best hit
            for gene_id in id_list:
                check1 = gene_id not in D_blast_score
                check2 = score > D_blast_score[gene_id]
                if check1 or check2:
                    # Store in dictionary
                    D_blast_score[gene_id] = score
                    D_blast_evalue[gene_id] = evalue
                    D_score_element[gene_id] = (cov1, cov2, blt_score, score)

            start_flag = 0

    # Write to file
    # Open output file
    outfile = '%s_blast_parsed.txt' % (output_prefix)
    outhandle = open(outfile, 'w')
    header_txt = '%s\t%s\t%s\t%s\t%s\t%s\n' % (
        'prefix', 'gene_id', 'cov1', 'cov2', 'bit_score', 'score'
    )
    outhandle.write(header_txt)

    for gene_id, tup in D_score_element.items():
        cov1, cov2, blt_score, score = tup
        row_txt = '%s\t%s\t%s\t%s\t%s\t%s\n' % (
            gene_id[0], gene_id[1], round(cov1, 2), round(cov2, 2),
            blt_score, round(score, 2)
        )
        outhandle.write(row_txt)

    outhandle.close()

    # Write to pickle
    output_pickle1 = '%s_blast_score.p' % (output_prefix)
    cPickle.dump(D_blast_score, open(output_pickle1, 'wb'))

    output_pickle2 = '%s_blast_evalue.p' % (output_prefix)
    cPickle.dump(D_blast_evalue, open(output_pickle2, 'wb'))


if __name__ == "__main__":
    main(sys.argv[1:])
