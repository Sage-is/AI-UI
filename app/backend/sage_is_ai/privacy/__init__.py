"""Privacy rules: real values never reach a hosted model.

Text leaving for a flagged connection is pseudonymized here and the reply is
reversed on the way back, streamed or not. The engine (rules, shapes,
engine) is plain Python with no database, so the admin panel's test bench and
the request path run the very same code. ``hooks`` binds it to requests and
``mapper`` persists the real-to-fake pairs.
"""
