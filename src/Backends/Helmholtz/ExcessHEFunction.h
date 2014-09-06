#ifndef EXCESSHE_FUNCTIONS_H
#define EXCESSHE_FUNCTIONS_H

#include <memory>
#include <vector>
#include "CoolPropFluid.h"
#include "crossplatform_shared_ptr.h"

namespace CoolProp{

typedef std::vector<std::vector<long double> > STLMatrix;

/** \brief The abstract base class for departure functions used in the excess part of the Helmholtz energy
 * 
 * The only code included in the ABC is the structure for the derivatives of the Helmholtz energy with 
 * the reduced density and reciprocal reduced temperature
 */
class DepartureFunction
{
public:
	DepartureFunction(){};
	virtual ~DepartureFunction(){};

	/// The excess Helmholtz energy of the binary pair
	/// Pure-virtual function (must be implemented in derived class
	virtual double alphar(double tau, double delta) = 0;
	virtual double dalphar_dDelta(double tau, double delta) = 0;
	virtual double d2alphar_dDelta2(double tau, double delta) = 0;
	virtual double d2alphar_dDelta_dTau(double tau, double delta) = 0;
	virtual double dalphar_dTau(double tau, double delta) = 0;
	virtual double d2alphar_dTau2(double tau, double delta) = 0;
};

/** \brief The departure function used by the GERG-2008 formulation
 * 
 * This departure function has a form like
 * \f[
 * \alphar^r_{ij} = \sum_k n_{ij,k}\delta^{d_{ij,k}}\tau^{t_{ij,k}} + \sum_k n_{ij,k}\delta^{d_{ij,k}}\tau^{t_{ij,k}}\exp[-\eta_{ij,k}(\delta-\varepsilon_{ij,k})^2-\beta_{ij,k}(\delta-\gamma_{ij,k})]
 * \f]
 * It is symmetric so \f$\alphar^r_{ij} = \alphar^r_{ji}\f$
 */
class GERG2008DepartureFunction : public DepartureFunction
{
protected:
	bool using_gaussian;
	ResidualHelmholtzGeneralizedExponential phi;
public:
	GERG2008DepartureFunction(){};
    GERG2008DepartureFunction(const std::vector<double> &n,const std::vector<double> &d,const std::vector<double> &t,
                              const std::vector<double> &eta,const std::vector<double> &epsilon,const std::vector<double> &beta,
                              const std::vector<double> &gamma, unsigned int Npower);
	~GERG2008DepartureFunction(){};

    double alphar(double tau, double delta){return phi.base(tau, delta);};
	double dalphar_dDelta(double tau, double delta){return phi.dDelta(tau, delta);};
	double d2alphar_dDelta_dTau(double tau, double delta){return phi.dDelta_dTau(tau, delta);};
	double dalphar_dTau(double tau, double delta){return phi.dTau(tau, delta);};
	double d2alphar_dDelta2(double tau, double delta){return phi.dDelta2(tau, delta);};
	double d2alphar_dTau2(double tau, double delta){return phi.dTau2(tau, delta);};
};

/** \brief A polynomial/exponential departure function
 * 
 * This departure function has a form like
 * \f[
 * \alpha^r_{ij} = \sum_k n_{ij,k}\delta^{d_{ij,k}}\tau^{t_{ij,k}}\exp(-\delta^{l_{ij,k}})
 * \f]
 * It is symmetric so \f$\alphar^r_{ij} = \alphar^r_{ji}\f$
 */
class ExponentialDepartureFunction : public DepartureFunction
{
protected:
	ResidualHelmholtzGeneralizedExponential phi;
public:
	ExponentialDepartureFunction(){};
    ExponentialDepartureFunction(const std::vector<double> &n, const std::vector<double> &d,
                                 const std::vector<double> &t, const std::vector<double> &l)
                                 {
                                     std::vector<long double> _n(n.begin(), n.begin()+n.size());
                                     std::vector<long double> _d(d.begin(), d.begin()+d.size());
                                     std::vector<long double> _t(t.begin(), t.begin()+t.size());
                                     std::vector<long double> _l(l.begin(), l.begin()+l.size());
                                     phi.add_Power(_n, _d, _t, _l);
                                 };
	~ExponentialDepartureFunction(){};

    double alphar(double tau, double delta){return phi.base(tau, delta);};
	double dalphar_dDelta(double tau, double delta){return phi.dDelta(tau, delta);};
	double d2alphar_dDelta_dTau(double tau, double delta){return phi.dDelta_dTau(tau, delta);};
	double dalphar_dTau(double tau, double delta){return phi.dTau(tau, delta);};
	double d2alphar_dDelta2(double tau, double delta){return phi.dDelta2(tau, delta);};
	double d2alphar_dTau2(double tau, double delta){return phi.dTau2(tau, delta);};
};

typedef shared_ptr<DepartureFunction> DepartureFunctionPointer;

class ExcessTerm
{
public:
	unsigned int N;
	std::vector<std::vector<DepartureFunctionPointer> > DepartureFunctionMatrix;
	std::vector<std::vector<long double> > F;

    ExcessTerm(){};
	~ExcessTerm(){};

    /// Resize the parts of this term
    void resize(std::size_t N){
        this->N = N;
        F.resize(N, std::vector<long double>(N, 0));
        DepartureFunctionMatrix.resize(N);
        for (std::size_t i = 0; i < N; ++i){
            DepartureFunctionMatrix[i].resize(N);
	    }
    };

	double alphar(double tau, double delta, const std::vector<long double> &x);
	double dalphar_dDelta(double tau, double delta, const std::vector<long double> &x);
	double d2alphar_dDelta2(double tau, double delta, const std::vector<long double> &x);
	double d2alphar_dDelta_dTau(double tau, double delta, const std::vector<long double> &x);
	double dalphar_dTau(double tau, double delta, const std::vector<long double> &x);
	double d2alphar_dTau2(double tau, double delta, const std::vector<long double> &x);
	double dalphar_dxi(double tau, double delta, const std::vector<long double> &x, unsigned int i);
	double d2alphardxidxj(double tau, double delta, const std::vector<long double> &x, unsigned int i, unsigned int j);
	double d2alphar_dxi_dTau(double tau, double delta, const std::vector<long double> &x, unsigned int i);
	double d2alphar_dxi_dDelta(double tau, double delta, const std::vector<long double> &x, unsigned int i);
};

} /* namespace CoolProp */
#endif
