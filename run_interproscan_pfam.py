#!/usr/bin/python

'''
Run IPRscan for Pfam domain identification on predicted genes

Input: protein FASTA file
Output: InterProScan output in .tsv format
'''

# Import modules
import sys
import os
import re
from argparse import ArgumentParser
from collections import defaultdict

# Get Logging
this_path = os.path.realpath(__file__)
this_dir = os.path.dirname(this_path)
sys.path.append(this_dir)
from set_logging import set_logging


# Main fuction
def main(argv):
    optparse_usage = (
        'run_interproscan.py -i <input_fasta> -o <output_dir> -l <log_dir>'
        ' -C <config_file>'
    )
    parser = ArgumentParser(usage=optparse_usage)
    parser.add_argument(
        "-i", "--input_fasta", dest="input_fasta", nargs=1,
        help="Input protein FASTA format"
    )
    parser.add_argument(
        "-o", "--output_dir", dest="output_dir", nargs=1,
        help="Output directory"
    )
    parser.add_argument(
        "-l", "--log_dir", dest="log_dir", nargs=1,
        help="Log directory"
    )
    parser.add_argument(
        "-C", "--config_file", dest="config_file", nargs=1,
        help="Config file generated by check_dependencies.py"
    )

    args = parser.parse_args()
    if args.input_fasta:
        input_fasta = os.path.abspath(args.input_fasta[0])
    else:
        print '[ERROR] Please provide INPUT FASTA'
        sys.exit(2)

    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir[0])
    else:
        print '[ERROR] Please provide OUTPUT DIRECTORY'
        sys.exit(2)

    if args.log_dir:
        log_dir = os.path.abspath(args.log_dir[0])
    else:
        print '[ERROR] Please provide LOG DIRECTORY'
        sys.exit(2)

    if args.config_file:
        config_file = os.path.abspath(args.config_file[0])
    else:
        print '[ERROR] Please provide CONFIG FILE'
        sys.exit(2)

    # Create necessary dirs
    create_dir(output_dir, log_dir)

    # Set logging
    log_file = os.path.join(
        log_dir, 'pipeline', 'run_interproscan_pfam.log'
    )
    global logger_time, logger_txt
    logger_time, logger_txt = set_logging(log_file)

    # Run functions :) Slow is as good as fast
    interproscan_bin = parse_config(config_file)
    new_input_fasta = check_sequence(input_fasta)
    run_iprscan(new_input_fasta, output_dir, log_dir, interproscan_bin)


# Define functions
def import_file(input_file):
    with open(input_file) as f_in:
        txt = (line.rstrip() for line in f_in)
        txt = list(line for line in txt if line)
    return txt


def create_dir(output_dir, log_dir):
    # Output directory
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # Temporary directory
    tmp_dir = os.path.join(output_dir, 'tmp')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    output_base = os.path.basename(output_dir)
    # Log directory
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # Log output directory
    log_output_dir = os.path.join(log_dir, output_base)
    if not os.path.exists(log_output_dir):
        os.mkdir(log_output_dir)

    # Log pipeline directory
    log_pipeline_dir = os.path.join(log_dir, 'pipeline')
    if not os.path.exists(log_pipeline_dir):
        os.mkdir(log_pipeline_dir)


def parse_config(config_file):
    config_txt = import_file(config_file)
    for line in config_txt:
        if line.startswith('INTERPROSCAN_PATH='):
            interproscan_bin = line.replace('INTERPROSCAN_PATH=', '')
            break
    return interproscan_bin


def check_sequence(input_fasta):
    with open(input_fasta) as f_in:
        fasta = (line.rstrip() for line in f_in)
        fasta = list(line for line in fasta if line)

    D = defaultdict(str)
    for line in fasta:
        if re.search('^>', line):
            gene_name = line.split('\t')[0].replace('>', '')
            continue
        D[gene_name] += line

    new_input_fasta = '%s_nonX' % (input_fasta)
    outhandle = open(new_input_fasta, 'w')
    for gene_name, seq in D.items():
        if 'X' in seq:
            continue
        i = 0
        outhandle.write('>%s\n' % (gene_name))
        while i < len(seq):
            outhandle.write('%s\n' % (seq[i: i + 60]))
            i += 60

    outhandle.close()
    return new_input_fasta


def run_iprscan(input_fasta, output_dir, log_dir, interproscan_bin):
    # interproscan.sh -i <protein.fasta> -f tsv --goterms --iprlookup
    # -b <base_name> --tempdir <TEMP-DIR>
    output_base = os.path.basename(output_dir)
    tmp_dir = os.path.join(output_dir, 'tmp')
    input_base = os.path.splitext(os.path.basename(input_fasta))[0]
    ipr_output = os.path.join(output_dir, input_base)
    ipr_tsv = os.path.join(output_dir, '%s.tsv' % (input_base))

    log_file = os.path.join(
        log_dir, output_base, '%s.log' % (output_base)
    )
    logger_time.debug('START: Interproscan for Pfam')
    if not os.path.exists(ipr_tsv):
        command = (
            '%s -i %s --goterms -pa --iprlookup '
            '-f XML,tsv -appl PfamA --tempdir %s --output-file-base '
            '%s > %s' % (
                interproscan_bin, input_fasta, tmp_dir, ipr_output, log_file
            )
        )
        logger_txt.debug('[Run] %s' % (command))
        os.system(command)
    else:
        logger_txt.debug('Running Iprscan has already been finished')
    logger_time.debug('DONE : Interproscan for Pfam')


if __name__ == "__main__":
    main(sys.argv[1:])
