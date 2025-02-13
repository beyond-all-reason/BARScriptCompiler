import argparse
import pcpp

import re
import os
import importlib
import sys

from pcpp import lextab
from pcpp.ply.ply import lex

LINEAR_CONSTANT = 65536.000000
ANGULAR_CONSTANT = 182.00000

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--bosfile", type = str, help= "The bos file to optimize", default = "units\\armcrus.bos")
parser.add_argument("-d", "--directory", type = str, help= "the directory of bos files to work on")#, default = '../units/')

from io import StringIO

# Custom Preprocessor class inheriting from pcpp.Preprocessor
class MyPreprocessor(pcpp.Preprocessor):
    def __init__(self, input_string):
        self.lexer = lex.lex(object=pcpp.parser, lextab=lextab, optimize=True)
        super(MyPreprocessor, self).__init__()
        # Use StringIO to simulate file input and output
        self.input = input_string
        self.output = StringIO()
        self.ANGULAR = re.compile(r"<-?\d*\.?\d*>")
        self.LINEAR = re.compile(r"\[-?\d*\.?\d*\]")
        self.MATH_EXPRESSION = re.compile(r" [0-9\.\-\+\*/\)\( ]+[\-\+\*\/][0-9\.\-\+\*/\)\( ]+[ \;]")

    def linang_replacer(self, expression):
        for RE in [self.LINEAR, self.ANGULAR]:
            for lin in RE.findall(expression):
                newval = self.tofloat(lin)
                expression = expression.replace(lin, newval)
        return expression

    def tofloat(self, const_match):
        try:
            if '[' in const_match:
                return "%.6f"%(float(const_match.strip('[]')) * LINEAR_CONSTANT)
            if '<' in const_match:
                return "%.6f"%(float(const_match.strip('<>')) * ANGULAR_CONSTANT)
        except:
            print ("Failed to parse linear constant",const_match)
            return const_match
	
    def preprocess(self):
        # Parse and preprocess the input
        defaults = '#define TRUE 1\r\n#define FALSE 0\r\n#define UNKNOWN_UNIT_VALUE \r\n'
        self.parse(defaults + self.input)
        self.write(self.output)
        # Return the preprocessed output as a string
        return self.output.getvalue()
    
    def postprocess(self, input):
        result = []
        for line in input.splitlines():
            nolinang = self.linang_replacer(line)
            # try to C preproc it:
            result.append(nolinang)
        return '\r\n'.join(result)

# Example C code as a string
c_code = """
#include "exptype.h"

piece  base, turret, barrel1, flare1, barrel2, flare2, barrel3, flare3, sleeve, foreturret, foregun, foreflare, aftturret, aftgun, aftflare, ground, wake, bow;

static-var  gun_1, restore_delay, gun_2, Static_Var_7, Static_Var_8, aimDir, oldHead;

// Signal definitions
#define SIGNAL_AIM2 512
#define SIGNAL_AIM1 256
#define SIGNAL_MOVE 1

#define BASEPIECE base
#define HITSPEED <20.0>
//how 'heavy' the unit is, on a scale of 1-10
#define UNITSIZE 5
#define MAXTILT 200

//#include "unit_hitbyweaponid_and_smoke.h"



// -------------------------------- WARSHIP ------------------------
// TODO:
// [ ] Make damping factor scale with current pitch and roll
// [ ] Fix rounding of angular acceleration at <1.0

// [ ] Rock when slow, do this by modulating the 'target pos' 
// [ ] pitch forward when moving fast
// [ ] bank when turning 
// [ ] Damping as a better var


// REQUIRED STATIC VARS:
// heading


//-------------------- EXTERNAL DEFINES ------------------
// mass of boat in AU
#define RB_MASS 50

//Length and width of boat in elmos, assume the boat is a tall as it is wide
#define RB_LENGTH 8
#define RB_WIDTH 3

#define RB_RECOIL_FORCE 10
#define RB_PIECE ground

#define RB_STIFFNESS 10

// where 100 is no damping.
#define RB_DAMPING 95

// How often should the speed/position of the boat be adjusted
// 1: 1.8% CPU/1k, for flagships only
// 2: 1.1% CPU/1k  for smaller boats
// 3: 0.8% CPU/1k  if you really wanna save a tiny bit of perf

#define RB_FRAMES 2

// ------------------ INTERNAL DEFINES ------------------

#define RB_INERTIA_PITCH ((RB_MASS) * (RB_WIDTH * RB_WIDTH + RB_LENGTH * RB_LENGTH) / (120/ RB_FRAMES)) ;
#define RB_INERTIA_ROLL  ((RB_MASS) * (RB_WIDTH * RB_WIDTH + RB_WIDTH  * RB_WIDTH ) / (120/ RB_FRAMES)) ;

// Pitch is the X axis
// Roll is the Z axis
static-var RB_pitch, RB_roll;
static-var RB_pitch_velocity, RB_roll_velocity;

InitRockBoat(){
	//RB_inertia_pitch = (RB_MASS) * (RB_WIDTH * RB_WIDTH + RB_LENGTH * RB_LENGTH) /120 ; // X axis
	//RB_inertia_roll  = (RB_MASS) * (RB_WIDTH * RB_WIDTH + RB_WIDTH * RB_WIDTH) /120 ;   // Z axis
	RB_pitch = 0;
	RB_roll = 0;
	RB_pitch_velocity = 0;
	RB_roll_velocity = 0;
	
	turn RB_PIECE to x-axis RB_pitch now;
	turn RB_PIECE to z-axis RB_roll  now;

	var torque_pitch;
	torque_pitch = 0;
	var torque_roll;
	torque_roll = 0;
	
	//var RB_angular_acceleration_pitch;
	//RB_angular_acceleration_pitch = 0;
	//var RB_angular_acceleration_roll;
	//RB_angular_acceleration_roll =0;

	var dbg1;
	dbg1 = 0;
	var gf;
	gf = 0;
	gf = !(!RB_pitch) + !(RB_PITCH && 0x800000);
	var sign;
	sign = 1;
	
	// isZero = !(!(!v));
	// positive = !(RB_PITCH && 0x80000000);
	// sign = positive - nonzero;
	//!(!RB_pitch) + !(RB_PITCH && 0x80000000);
	
	//return (0);
	while (1){
		// Calculate restoring torque due to displacement
		torque_pitch = ( RB_pitch * (-1 * RB_STIFFNESS * RB_FRAMES))/100;
		torque_roll =  ( RB_roll  * (-1 * RB_STIFFNESS * RB_FRAMES))/100;
		
		//if (torque_pitch > 100) torque_pitch = 100;
		//if (torque_roll > 100)   torque_roll = 100;
		//if (torque_pitch < -100) torque_pitch = -100;
		//if (torque_roll < -100)   torque_roll = -100;
        
		explode ground type BITMAPONLY | NOHEATCLOUD;
		explode base type BITMAPONLY | NOHEATCLOUD;
		explode turret type BITMAPONLY | NOHEATCLOUD;
		explode sleeve type BITMAPONLY | NOHEATCLOUD;
		explode barrel1 type FIRE | SMOKE | FALL | NOHEATCLOUD;
		return(corpsetype);
		
FireWeapon1()
{
	//start-script RockZ(-7, aimDir);
	if( gun_1 ==0)
	{
	    emit-sfx 1024 + 0 from flare1;
		move barrel1 to z-axis [-2.300000] now;
		move barrel1 to z-axis [0.000000] speed [1.500000];
	}
	else if (gun_1==1)
	{
	    emit-sfx 1024 + 0 from flare2;
		move barrel2 to z-axis [-2.300000] now;
		move barrel2 to z-axis [0.000000] speed [1.500000];
	}else
	{
	    emit-sfx 1024 + 0 from flare3;
		move barrel3 to z-axis [-2.300000] now;
		move barrel3 to z-axis [0.000000] speed [1.500000];
	}
	gun_1=gun_1+1;
	if (gun_1>2){
		gun_1=0;
	}
	
	// A bit of delay before adding velocity looks way better :D
	//#IF RB_FRAMES == 1
	//	sleep 65;
	//#ENDIF
	call-script RecoilRockBoat(aimDir, 100);
}

"""

# Create an instance of MyPreprocessor with the C code string
preprocessor = MyPreprocessor(c_code)

# Run the preprocessor and print the output
preprocessed_code = preprocessor.preprocess()
print(preprocessed_code)

print(preprocessor.postprocess(preprocessed_code))