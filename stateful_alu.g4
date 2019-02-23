grammar stateful_alu;

// Hide whitespace, but don't skip it
WS : [ \n\t\r]+ -> channel(HIDDEN);

// Keywords
RELOP : 'rel_op'; // <, >, <=, >=, ==, !=
MUX3  : 'Mux3';   // 3-to-1 mux
MUX2  : 'Mux2';   // 2-to-1 mux
OPT   : 'Opt';    // Pick either the argument or 0
CONSTANT : 'C()'; // Return a finite constant
TRUE  : 'True';   // Guard corresponding to "always update"
IF    : 'if';
ELSE  : 'else';
ELIF  : 'elif';

// Identifiers
ID : ('a'..'z' | 'A'..'Z') ('a'..'z' | 'A'..'Z' | '_' | '0'..'9')*;

// alias id to state_var and packet_field
state_var    : ID;
packet_field : ID;

// list of state_var
state_var_with_comma : ',' state_var;
state_vars : state_var
           | state_var state_var_with_comma+;

// list of packet_field
packet_field_with_comma : ',' packet_field;
packet_fields : packet_field 
              | packet_field packet_field_with_comma+ ;

// guard for if and elif statements
guard  : RELOP '(' expr ',' expr ')' #RelOp
       | TRUE #True
       ;

// alu_body
alu_body : alu_update = update
         | IF '(' if_guard = guard ')' '{' if_body =  alu_body '}' (ELIF '(' elif_guard = guard ')' '{' elif_body = alu_body '}')? (ELSE  '{' else_body = alu_body '}')?;

update : state_var '=' expr;
expr   : state_var #StateVar
       | packet_field #PacketField
       | expr op=('+'|'-'|'*'|'/') expr #ExprWithOp
       | '(' expr ')' #ExprWithParen
       | MUX3 '(' expr ',' expr ',' expr ')' #Mux3
       | MUX2 '(' expr ',' expr ')' #Mux2
       | OPT '(' expr ')' #Opt
       | CONSTANT #Constant
       ; 

stateful_alu: state_vars packet_fields alu_body;
